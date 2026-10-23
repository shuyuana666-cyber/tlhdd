"""Offline integration tests: real Redis protocol model and boto3 against Moto S3.

python -B -m unittest discover -s tests -v
"""
from __future__ import annotations

import importlib.util
import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

import boto3
import fakeredis
from moto import mock_aws
from PIL import Image

import cache_service as cache
import content_service
import database
import media_storage as media
import server
import uploads


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"TLHDD_REDIS_URL": "redis://unused", "TLHDD_CACHE_PREFIX": "tests", "TLHDD_CACHE_TTL": "60"})
        self.env.start()
        self.client = fakeredis.FakeRedis(decode_responses=True)
        self.old_client, self.old_retry = cache._client, cache._retry_at
        cache._client, cache._retry_at = self.client, 0
        self.key = cache.route_cache_key("/api/site", {})

    def tearDown(self):
        cache._client, cache._retry_at = self.old_client, self.old_retry
        self.env.stop()

    def test_hit_reduces_database_load_and_has_ttl(self):
        loader = Mock(return_value={"title": "中文"})
        self.assertEqual(cache.get_or_load(self.key, loader)[1], "miss")
        self.assertEqual(cache.get_or_load(self.key, loader), ({"title": "中文"}, "hit"))
        loader.assert_called_once()
        keys = list(self.client.scan_iter("tests:*:" + self.key))
        self.assertTrue(0 < self.client.ttl(keys[0]) <= 66)

    def test_successful_commit_invalidates_direct_and_bulk_writes(self):
        loader = Mock(side_effect=[{"n": 1}, {"n": 2}])
        cache.get_or_load(self.key, loader)
        raw = MagicMock()
        raw.cursor.return_value.description = None
        with patch.dict(os.environ, {"MYSQL_PASSWORD": "test"}), patch.object(database.pymysql, "connect", return_value=raw):
            with database.connect() as conn:
                conn.execute("DELETE FROM `vehicles` WHERE id IN (?,?)", (1, 2))
                self.assertEqual(cache.get_or_load(self.key, loader)[1], "hit")
        raw.commit.assert_called_once()
        self.assertEqual(cache.get_or_load(self.key, loader), ({"n": 2}, "miss"))

    def test_rollback_and_failed_commit_do_not_invalidate(self):
        for failure in ("rollback", "commit"):
            with self.subTest(failure=failure):
                loader = Mock(return_value={"n": 1})
                cache.get_or_load(self.key, loader)
                raw = MagicMock()
                raw.cursor.return_value.description = None
                if failure == "commit":
                    raw.commit.side_effect = RuntimeError("commit failed")
                with patch.dict(os.environ, {"MYSQL_PASSWORD": "test"}), patch.object(database.pymysql, "connect", return_value=raw):
                    with self.assertRaises(RuntimeError):
                        with database.connect() as conn:
                            conn.execute("UPDATE vehicles SET title=? WHERE id=?", ("test", 1))
                            if failure == "rollback":
                                raise RuntimeError("rollback")
                self.assertEqual(cache.get_or_load(self.key, loader)[1], "hit")
                raw.close.assert_called_once()

    def test_old_reader_cannot_refill_current_generation(self):
        def old_read():
            cache.invalidate_public_cache()
            return {"value": "old"}
        cache.get_or_load(self.key, old_read)
        self.assertEqual(cache.get_or_load(self.key, lambda: {"value": "new"}), ({"value": "new"}, "miss"))

    def test_evicted_generation_is_not_reused(self):
        cache.get_or_load(self.key, lambda: {"old": True})
        self.client.delete("tests:generation")
        self.assertEqual(cache.get_or_load(self.key, lambda: {"new": True})[0], {"new": True})

    def test_failure_bypasses_and_recovers(self):
        with patch.object(self.client, "get", side_effect=ConnectionError("secret")):
            self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": True})[1], "bypass")
        self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": True})[1], "bypass")
        cache._retry_at = 0
        self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": True})[1], "miss")

    def test_disabled_cache_uses_no_redis(self):
        with patch.dict(os.environ, {"TLHDD_REDIS_URL": ""}), patch.object(self.client, "get") as get:
            self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": True})[1], "bypass")
            get.assert_not_called()

    def test_private_search_and_unbounded_requests_never_cache(self):
        for path, params in [
            ("/api/admin/all", {}), ("/api/auth/me", {}), ("/api/messages/threads/1", {}),
            ("/api/search", {"q": ["a"]}), ("/api/vehicles", {"q": ["a"]}),
            ("/api/parts", {"page": ["21"]}), ("/api/site", {"random": ["a"]}),
            ("/api/news", {"category": ["a", "b"]}), ("/api/forum/posts", {}),
        ]:
            self.assertIsNone(cache.route_cache_key(path, params))

    def test_route_keys_keep_filters_separate_and_order_stable(self):
        key = cache.route_cache_key
        self.assertEqual(key("/api/vehicles", {"page": ["2"], "brand": ["A"]}), key("/api/vehicles", {"brand": ["A"], "page": ["2"]}))
        self.assertNotEqual(key("/api/vehicles", {"type": ["new"]}), key("/api/vehicles", {"type": ["used"]}))

    def test_error_and_large_payload_not_cached(self):
        loader = Mock(side_effect=ValueError("not found"))
        for _ in range(2):
            with self.assertRaises(ValueError):
                cache.get_or_load(self.key, loader)
        self.assertEqual(loader.call_count, 2)
        self.assertEqual(cache.get_or_load(self.key, lambda: "x" * (1024 * 1024 + 1))[1], "miss")
        self.assertEqual(cache.get_or_load(self.key, lambda: "small")[0], "small")

    def test_concurrent_misses_coalesce(self):
        calls = []
        def loader():
            calls.append(1)
            time.sleep(0.03)
            return {"ok": 1}
        threads = [threading.Thread(target=lambda: cache.get_or_load(self.key, loader)) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(calls), 1)

    def test_real_redis_client_over_local_protocol(self):
        tcp = fakeredis.TcpFakeServer(("127.0.0.1", 0), server_type="redis")
        thread = threading.Thread(target=tcp.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(os.environ, {"TLHDD_REDIS_URL": f"redis://127.0.0.1:{tcp.server_address[1]}/0"}), patch.object(cache, "_client", None):
                self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": 1})[1], "miss")
                self.assertEqual(cache.get_or_load(self.key, lambda: {"ok": 2}), ({"ok": 1}, "hit"))
                cache._client.close()
        finally:
            tcp.shutdown()
            tcp.server_close()
            thread.join()


class QueryTests(unittest.TestCase):
    def test_page_sections_use_two_queries_and_preserve_visibility_and_order(self):
        for admin in (False, True):
            with self.subTest(admin=admin):
                conn = MagicMock()
                conn.__enter__.return_value = conn
                conn.execute.return_value.fetchall.side_effect = [
                    [{"id": 2, "page_key": "home"}, {"id": 3, "page_key": "about"}, {"id": 4, "page_key": "home"}],
                    [{"id": 6, "section_id": 3}, {"id": 5, "section_id": 2}, {"id": 7, "section_id": 3}],
                ]
                with patch.object(content_service, "connect", return_value=conn) as connect:
                    result = content_service.list_page_sections(admin=admin)
                connect.assert_called_once()
                self.assertEqual(conn.execute.call_count, 2)
                self.assertEqual([i["id"] for i in result[1]["items"]], [6, 7])
                self.assertEqual(result[2]["items"], [])
                sql, ids = conn.execute.call_args.args
                self.assertEqual(ids, (2, 3, 4))
                self.assertEqual("AND is_active=1" in sql, not admin)

    def test_empty_page_does_not_query_children(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = []
        with patch.object(content_service, "connect", return_value=conn):
            self.assertEqual(content_service.list_page_sections(), [])
        self.assertEqual(conn.execute.call_count, 1)

    def test_only_public_tables_invalidate(self):
        self.assertTrue(cache.changes_public_data("INSERT INTO news_articles (id) VALUES (?)"))
        self.assertTrue(cache.changes_public_data("INSERT IGNORE INTO site_settings (`key`) VALUES (?)"))
        for sql in ("SELECT * FROM vehicles", "UPDATE admin_sessions SET expires_at=?", "INSERT INTO chat_messages (id) VALUES (?)"):
            self.assertFalse(cache.changes_public_data(sql))

    def test_slow_query_logs_no_values(self):
        with patch.dict(os.environ, {"TLHDD_SLOW_SQL_MS": "1"}), self.assertLogs("database", level="WARNING") as captured:
            database.DatabaseConnection._log_slow("SELECT * FROM public_users WHERE account='private'", time.perf_counter() - 1)
        self.assertNotIn("private", str(captured.output))
        self.assertIn("fingerprint=", str(captured.output))


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.aws = mock_aws()
        self.aws.start()
        self.env = patch.dict(os.environ, {"TLHDD_MEDIA_BACKEND": "s3", "TLHDD_S3_BUCKET": "test-media",
            "TLHDD_S3_REGION": "us-east-1", "TLHDD_S3_ENDPOINT": "", "TLHDD_S3_PREFIX": "site",
            "TLHDD_MEDIA_PUBLIC_BASE": "https://cdn.example.com", "TLHDD_MEDIA_REDIRECT": "1",
            "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing", "AWS_SESSION_TOKEN": "testing"})
        self.env.start()
        media.settings.cache_clear()
        self.client = boto3.client("s3", region_name="us-east-1")
        self.client.create_bucket(Bucket="test-media")
        self.patches = [patch.object(media, "ROOT", self.root), patch.object(media, "INDEX_PATH", self.root / "data/media.db"),
                        patch.object(media, "_client", self.client), patch.object(uploads, "UPLOAD_DIR", self.root / "uploads"),
                        patch.object(server, "BASE_DIR", self.root)]
        for item in self.patches:
            item.start()
        self.relative = "/uploads/2026/10/test.png"
        self.path = self.root / self.relative.lstrip("/")
        self.path.parent.mkdir(parents=True)
        Image.new("RGB", (20, 20), "red").save(self.path)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.env.stop()
        self.aws.stop()
        media.settings.cache_clear()
        self.tmp.cleanup()

    def test_upload_verify_idempotence_and_content_headers(self):
        self.assertEqual(media.public_media_url(self.relative), self.relative)
        self.assertTrue(media.publish_file(self.path, verify_download=True))
        self.assertFalse(media.publish_file(self.path, verify_download=True))
        response = self.client.get_object(Bucket="test-media", Key="site" + self.relative)
        self.assertEqual(response["Body"].read(), self.path.read_bytes())
        self.assertEqual(response["ContentType"], "image/png")
        self.assertIn("max-age=", response["CacheControl"])
        self.assertEqual(media.public_media_url(self.relative), "https://cdn.example.com/site" + self.relative)

    def test_unverified_or_changed_local_file_stays_local(self):
        self.assertEqual(media.public_media_url("/uploads/2026/10/missing.png"), "/uploads/2026/10/missing.png")
        media.publish_file(self.path)
        self.path.write_bytes(b"new file")
        self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_index_failure_stays_local(self):
        media.INDEX_PATH.parent.mkdir(parents=True)
        media.INDEX_PATH.write_bytes(b"corrupt index")
        self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_bucket_or_prefix_change_does_not_reuse_index(self):
        media.publish_file(self.path)
        with patch.dict(os.environ, {"TLHDD_S3_PREFIX": "other"}):
            media.settings.cache_clear()
            self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_disable_redirect_immediately_restores_old_paths(self):
        media.publish_file(self.path)
        with patch.dict(os.environ, {"TLHDD_MEDIA_REDIRECT": "0"}):
            self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_unsafe_paths_are_never_redirected(self):
        for value in ("/uploads/../data/a.png", "/uploads/2026/10/a.png?x=1", "https://evil.example/a.png", "/uploads/2026/10/a.html", "/data/private.png", "/uploads/2026/10/%2e%2e.png"):
            self.assertEqual(media.public_media_url(value), value)

    def test_upload_images_publish_original_and_both_variants(self):
        result = uploads._save_admin_image("test.png", self.path.read_bytes(), "image/png")
        self.assertTrue(result["url"].startswith("/uploads/"))
        for field in ("url", "thumb_url", "optimized_url"):
            self.assertTrue(media.public_media_url(result[field]).startswith("https://cdn.example.com/"))
            self.assertTrue((self.root / result[field].lstrip("/")).is_file())

    def test_invalid_image_does_not_reach_s3(self):
        with patch.object(media, "publish_file") as publish:
            with self.assertRaises(ValueError):
                uploads._save_admin_image("fake.png", b"not png", "image/png")
            publish.assert_not_called()

    def test_failed_upload_is_not_registered_or_silently_successful(self):
        with patch.object(self.client, "upload_file", side_effect=RuntimeError("password must not leak")):
            with self.assertRaises(media.StorageUnavailable) as error:
                media.publish_file(self.path)
        self.assertNotIn("password", str(error.exception))
        self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_failed_forum_upload_releases_quota(self):
        with patch.object(uploads, "parse_multipart_file", return_value=("test.png", self.path.read_bytes(), "image/png")), \
             patch.object(uploads, "reserve_forum_upload_quota") as reserve, \
             patch.object(uploads, "release_forum_upload_quota") as release, \
             patch.object(uploads, "publish_upload", side_effect=media.StorageUnavailable("unavailable")):
            user = {"id": 1}
            with self.assertRaises(media.StorageUnavailable):
                uploads.save_forum_media_file(Mock(), user)
            reserve.assert_called_once()
            release.assert_called_once_with(user, self.path.stat().st_size)

    def test_multipart_video_round_trip(self):
        video = self.path.with_suffix(".mp4")
        video.write_bytes(b"video" * (4 * 1024 * 1024))
        self.assertTrue(media.publish_file(video, verify_download=True))
        self.assertFalse(media.publish_file(video))

    def test_local_backend_upload_never_contacts_cloud(self):
        with patch.dict(os.environ, {"TLHDD_MEDIA_BACKEND": "local"}), patch.object(media, "publish_file") as publish:
            media.settings.cache_clear()
            uploads._save_admin_image("a.png", self.path.read_bytes(), "image/png")
            publish.assert_not_called()

    def test_real_s3_client_configuration(self):
        with patch.object(media, "_client", None):
            self.assertTrue(media.publish_file(self.path, verify_download=True))

    def test_download_verification_rejects_tampered_object(self):
        media.publish_file(self.path)
        head = self.client.head_object(Bucket="test-media", Key="site" + self.relative)
        self.client.put_object(Bucket="test-media", Key="site" + self.relative,
                               Body=b"x" * self.path.stat().st_size, Metadata=head["Metadata"])
        with self.assertRaises(media.StorageUnavailable):
            media.publish_file(self.path, verify_download=True)
        self.assertEqual(media.public_media_url(self.relative), self.relative)

    def test_migration_preview_and_apply_are_idempotent(self):
        script = Path(__file__).resolve().parents[1] / "scripts/migrate_media.py"
        spec = importlib.util.spec_from_file_location("migration_test", script)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with patch.object(migration, "ROOT", self.root):
            with patch("sys.argv", ["migrate_media.py"]), patch("sys.stdout", new_callable=io.StringIO) as output, patch.object(media, "s3_client") as client:
                migration.main()
                self.assertEqual(json.loads(output.getvalue())["mode"], "preview")
                client.assert_not_called()
            for expected in (1, 0):
                with patch("sys.argv", ["migrate_media.py", "--apply", "--verify-download"]), patch("sys.stdout", new_callable=io.StringIO) as output:
                    migration.main()
                    self.assertEqual(json.loads(output.getvalue())["uploaded"], expected)

    def test_rewriting_does_not_mutate_cached_or_database_payload(self):
        media.publish_file(self.path)
        payload = {"gallery": [self.relative], "image_url": self.relative}
        result = media.rewrite_public_media(payload)
        self.assertEqual(payload["image_url"], self.relative)
        self.assertNotEqual(result["image_url"], self.relative)

    def test_http_redirect_head_get_and_csp(self):
        media.publish_file(self.path)
        handler = server.TlhddHandler
        with server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                for method in ("GET", "HEAD"):
                    conn = http.client.HTTPConnection(*httpd.server_address)
                    conn.request(method, self.relative)
                    response = conn.getresponse()
                    self.assertEqual(response.status, 302)
                    self.assertEqual(response.getheader("Location"), "https://cdn.example.com/site" + self.relative)
                    self.assertEqual(response.getheader("Cache-Control"), "no-store")
                    self.assertIn("media-src 'self' blob: https://cdn.example.com;", response.getheader("Content-Security-Policy"))
                    self.assertEqual(response.read(), b"")
                    conn.close()
            finally:
                httpd.shutdown()
                thread.join()


class PublicHTTPTests(unittest.TestCase):
    setUp = CacheTests.setUp
    tearDown = CacheTests.tearDown
    def test_http_cache_public_only_and_not_found(self):
        handler = server.TlhddHandler
        with patch.object(server, "public_vehicle_payload", return_value={"vehicles": [{"id": 1}]}) as load, \
             patch.object(server, "get_public_vehicle", side_effect=ValueError("not found")), \
             server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            def request(path):
                conn = http.client.HTTPConnection(*httpd.server_address)
                conn.request("GET", path)
                response = conn.getresponse()
                result = response.status, response.getheader("X-Data-Cache"), response.getheader("Cache-Control"), response.read()
                conn.close()
                return result
            try:
                self.assertEqual(request("/api/vehicles")[:3], (200, "miss", "no-store"))
                self.assertEqual(request("/api/vehicles")[:3], (200, "hit", "no-store"))
                load.assert_called_once()
                for path in ("/api/admin/me", "/api/auth/me"):
                    self.assertEqual(request(path)[:2], (401, None))
                self.assertEqual(request("/api/vehicles/999")[:2], (404, None))
            finally:
                httpd.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
