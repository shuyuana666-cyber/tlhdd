"""S3-compatible media publishing with a local mirror and a verified-object index.

Database URLs stay relative. Only indexed objects can be served via the CDN.
The local mirror remains available for rollback and derivative discovery.
"""
from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import re
import sqlite3
import threading
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "data" / "media-objects.db"
_client_lock = threading.Lock()
_index_lock = threading.Lock()
_client = None
_MEDIA = re.compile(
    r"/(?:uploads/[0-9]{4}/[0-9]{2}|assets/(?:default-media|images)(?:/[A-Za-z0-9_-]+)*)/"
    r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:jpg|jpeg|png|webp|gif|avif|svg|ico|mp4|webm|mov)", re.IGNORECASE,
)


class StorageUnavailable(RuntimeError):
    pass


def _https_url(value: str, name: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or any(c.isspace() for c in value)
            or not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~-]+)*/?", value)
            or any(part in {".", ".."} for part in parsed.path.split("/"))):
        raise ValueError(f"{name} must be an HTTPS URL without credentials, query or fragment")
    return value.rstrip("/")


@lru_cache(maxsize=1)
def settings() -> dict[str, str]:
    backend = os.environ.get("TLHDD_MEDIA_BACKEND", "local").strip().lower()
    if backend not in {"local", "s3"}:
        raise ValueError("TLHDD_MEDIA_BACKEND must be local or s3")
    base = os.environ.get("TLHDD_MEDIA_PUBLIC_BASE", "").strip()
    endpoint = os.environ.get("TLHDD_S3_ENDPOINT", "").strip()
    bucket = os.environ.get("TLHDD_S3_BUCKET", "").strip()
    prefix = os.environ.get("TLHDD_S3_PREFIX", "").strip("/")
    if base:
        base = _https_url(base, "TLHDD_MEDIA_PUBLIC_BASE")
    if endpoint:
        endpoint = _https_url(endpoint, "TLHDD_S3_ENDPOINT")
    if prefix and not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", prefix):
        raise ValueError("TLHDD_S3_PREFIX must contain simple path segments")
    if (backend == "s3" or base) and not bucket:
        raise ValueError("TLHDD_S3_BUCKET is required")
    namespace = hashlib.sha256(f"{endpoint}|{bucket}|{prefix}".encode()).hexdigest()
    return {"backend": backend, "base": base, "endpoint": endpoint, "bucket": bucket,
            "prefix": prefix, "namespace": namespace,
            "region": os.environ.get("TLHDD_S3_REGION", "us-east-1")}


def media_path(value: str) -> str | None:
    if not isinstance(value, str) or not _MEDIA.fullmatch(value) or ".." in value:
        return None
    return value.lstrip("/")


def _object_key(relative: str) -> str:
    return "/".join(part for part in (settings()["prefix"], relative) if part)


def s3_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                import boto3
                from botocore.config import Config
                config = settings()
                # boto3 uses environment credentials / instance roles; never embed secrets.
                _client = boto3.client(
                    "s3", endpoint_url=config["endpoint"] or None, region_name=config["region"],
                    config=Config(signature_version="s3v4", connect_timeout=3, read_timeout=30,
                                  retries={"mode": "standard", "total_max_attempts": 2},
                                  s3={"addressing_style": os.environ.get("TLHDD_S3_ADDRESSING_STYLE", "auto")},
                                  request_checksum_calculation="when_required",
                                  response_checksum_validation="when_required"),
                )
    return _client


def _register(relative: str, digest: str, size: int, mtime_ns: int) -> None:
    # One application process per local index. SQLite serializes the migration CLI
    # and application writers too; no JSON lost-update race between processes.
    with _index_lock:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(INDEX_PATH, timeout=10)) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS objects (
                namespace TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL,
                size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                PRIMARY KEY(namespace, path))""")
            conn.execute("INSERT OR REPLACE INTO objects VALUES (?, ?, ?, ?, ?)",
                         (settings()["namespace"], relative, digest, size, mtime_ns))


def _forget(relative: str) -> None:
    if INDEX_PATH.is_file():
        try:
            with closing(sqlite3.connect(INDEX_PATH, timeout=1)) as conn, conn:
                conn.execute("DELETE FROM objects WHERE namespace=? AND path=?", (settings()["namespace"], relative))
        except (sqlite3.Error, OSError):
            pass  # Unreadable indexes already cause local fallback.


def _media_urls(values) -> dict[str, str]:
    config = settings()
    if os.environ.get("TLHDD_MEDIA_REDIRECT", "0") != "1" or not config["base"]:
        return {}
    paths = {relative for value in values if (relative := media_path(value))}
    if not paths or not INDEX_PATH.is_file():
        return {}
    mapping = {}
    try:
        with closing(sqlite3.connect(f"{INDEX_PATH.as_uri()}?mode=ro", uri=True, timeout=0.2)) as conn:
            # One connection per payload, rather than opening one per image.
            ordered = sorted(paths)
            for offset in range(0, len(ordered), 500):
                chunk = ordered[offset:offset + 500]
                placeholders = ",".join("?" for _ in chunk)
                rows = conn.execute(
                    f"SELECT path, size, mtime_ns FROM objects WHERE namespace=? AND path IN ({placeholders})",
                    [config["namespace"], *chunk],
                ).fetchall()
                for relative, size, mtime_ns in rows:
                    local = ROOT / relative
                    if local.exists():
                        stat = local.stat()
                        if stat.st_size != size or stat.st_mtime_ns != mtime_ns:
                            continue  # Republish changed local objects first.
                    mapping["/" + relative] = config["base"] + "/" + quote(_object_key(relative), safe="/")
        return mapping
    except (sqlite3.Error, OSError):
        return {}


def public_media_url(value: str) -> str:
    return _media_urls([value]).get(value, value)


def rewrite_public_media(payload):
    """Return a copy: cached data and editable database URLs stay relative."""
    strings = set()
    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str):
            strings.add(value)
    collect(payload)
    mapping = _media_urls(strings)
    def rewrite(value):
        if isinstance(value, dict):
            return {key: rewrite(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rewrite(child) for child in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    return rewrite(payload)


def publish_file(path: Path, *, verify_download: bool = False) -> bool:
    """Upload/verify and index one public file. Return True if a transfer was needed."""
    relative = None
    try:
        relative = path.relative_to(ROOT).as_posix()
        if (path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve())
                or not media_path("/" + relative)):
            raise ValueError("Not an allowed media path")
        # Reject linked directories, including Windows junctions.
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in path.parents if p != ROOT and p.is_relative_to(ROOT)):
            raise ValueError("Linked media directories are not supported")
        before = path.stat()
        with path.open("rb") as source:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
            digest = hasher.hexdigest()
        client = s3_client()
        bucket, key = settings()["bucket"], _object_key(relative)
        from botocore.exceptions import ClientError
        try:
            head = client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey", "NotFound"}:
                raise
            head = {}
        transferred = head.get("ContentLength") != before.st_size or head.get("Metadata", {}).get("sha256") != digest
        if transferred:
            from boto3.s3.transfer import TransferConfig
            client.upload_file(str(path), bucket, key, ExtraArgs={
                "ContentType": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "CacheControl": "public, max-age=2592000",
                "Metadata": {"sha256": digest},
            }, Config=TransferConfig(multipart_threshold=16 * 1024 * 1024,
                                     multipart_chunksize=8 * 1024 * 1024, max_concurrency=3))
            head = client.head_object(Bucket=bucket, Key=key)
        if head.get("ContentLength") != before.st_size or head.get("Metadata", {}).get("sha256") != digest:
            raise RuntimeError("Object verification failed")
        if verify_download:
            body = client.get_object(Bucket=bucket, Key=key)["Body"]
            try:
                remote_hash = hashlib.sha256()
                for chunk in iter(lambda: body.read(1024 * 1024), b""):
                    remote_hash.update(chunk)
                if remote_hash.hexdigest() != digest:
                    raise RuntimeError("Downloaded object checksum mismatch")
            finally:
                body.close()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("Local file changed during publishing")
        _register(relative, digest, after.st_size, after.st_mtime_ns)
        return transferred
    except Exception as exc:
        if relative:
            _forget(relative)
        logging.getLogger(__name__).error("Object storage publishing failed (%s)", type(exc).__name__)
        raise StorageUnavailable("媒体存储暂时不可用，请稍后重试") from exc


def publish_upload(result: dict) -> dict:
    if settings()["backend"] == "s3":
        for field in ("url", "optimized_url", "thumb_url"):
            if result.get(field):
                publish_file(ROOT / result[field].lstrip("/"))
    # Upload responses remain local URLs so existing admin/forum validation works.
    return result
