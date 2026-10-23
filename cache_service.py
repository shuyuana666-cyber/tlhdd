"""Optional Redis cache for public JSON only; database remains authoritative."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)
_client: Any = None
_retry_at = 0.0
_init_lock = threading.Lock()
_locks = [threading.Lock() for _ in range(64)]
PUBLIC_TABLES = {
    "vehicles", "parts", "catalog_terms", "hero_slides", "home_metrics",
    "site_settings", "page_sections", "page_section_items", "page_media", "news_articles",
}
_WRITE = re.compile(
    r"^\s*(?:INSERT\s+(?:IGNORE\s+)?INTO|REPLACE\s+INTO|UPDATE|DELETE\s+FROM)\s+`?(\w+)`?\b",
    re.IGNORECASE,
)


def changes_public_data(sql: str) -> bool:
    match = _WRITE.match(sql)
    return bool(match and match.group(1).lower() in PUBLIC_TABLES)


def _prefix() -> str:
    return os.environ.get("TLHDD_CACHE_PREFIX", "tlhdd:public:v1").strip() or "tlhdd:public:v1"


def _failed(exc: Exception) -> None:
    global _retry_at
    # Never log URLs, passwords, SQL parameters, or payload contents.
    if time.monotonic() >= _retry_at:
        log.warning("Redis unavailable (%s); using MySQL", type(exc).__name__)
    _retry_at = time.monotonic() + 5


def _redis():
    global _client
    if not os.environ.get("TLHDD_REDIS_URL", "").strip() or time.monotonic() < _retry_at:
        return None
    if _client is None:
        with _init_lock:
            if _client is None:
                try:
                    import redis
                    from redis.backoff import NoBackoff
                    from redis.retry import Retry
                    _client = redis.Redis.from_url(
                        os.environ["TLHDD_REDIS_URL"], socket_connect_timeout=0.2,
                        socket_timeout=0.2, max_connections=16, decode_responses=True,
                        retry_on_timeout=False,
                        retry=Retry(NoBackoff(), 0),
                    )
                except Exception as exc:
                    _failed(exc)
                    return None
    return _client


def invalidate_public_cache() -> None:
    """Call only after a successful commit. UUIDs prevent generation reuse on eviction."""
    client = _redis()
    if client is not None:
        try:
            client.set(_prefix() + ":generation", uuid.uuid4().hex)
        except Exception as exc:
            _failed(exc)


def route_cache_key(path: str, params: dict[str, list[str]]) -> str | None:
    """Bound key cardinality. Searches, arbitrary parameters and private routes bypass."""
    allowed: set[str]
    if path == "/api/site":
        allowed = set()
    elif path == "/api/news":
        allowed = {"category"}
    elif path in {"/api/vehicles", "/api/parts"}:
        allowed = {"page", "page_size", "category", "type", "brand", "model", "id"}
    elif re.fullmatch(r"/api/(vehicles|parts)/[1-9][0-9]{0,17}", path):
        allowed = {"type"}
    elif re.fullmatch(r"/api/news/[\w-]{1,120}", path):
        allowed = set()
    elif re.fullmatch(r"/api/pages/[a-z][a-z0-9_-]{0,63}", path):
        allowed = set()
    else:
        return None
    if set(params) - allowed:
        return None
    if any(len(values) != 1 or len(values[0]) > 64 for values in params.values()):
        return None
    try:
        if not 1 <= int(params.get("page", ["1"])[0]) <= 20:
            return None
    except ValueError:
        return None
    canonical = json.dumps([path, sorted((key, values[0]) for key, values in params.items())], ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_or_load(key: str | None, loader: Callable[[], Any]) -> tuple[Any, str]:
    client = _redis() if key is not None else None
    if client is None:
        return loader(), "bypass"
    try:
        generation_key = _prefix() + ":generation"
        generation = client.get(generation_key)
        if generation is None:
            client.set(generation_key, uuid.uuid4().hex, nx=True)
            generation = client.get(generation_key)
        if generation is None:
            return loader(), "bypass"
        # A concurrent writer rotates generation; an old reader can only fill its old key.
        data_key = f"{_prefix()}:{generation}:{key}"
        value = client.get(data_key)
        if value is not None:
            return json.loads(value), "hit"
    except Exception as exc:
        _failed(exc)
        return loader(), "bypass"

    lock = _locks[int(key[:8], 16) % len(_locks)]
    # Coalesce misses within this threaded application without unbounded waits.
    if not lock.acquire(timeout=0.25):
        return loader(), "bypass"
    try:
        try:
            value = client.get(data_key)
            if value is not None:
                return json.loads(value), "hit"
        except Exception as exc:
            _failed(exc)
            return loader(), "bypass"
        payload = loader()  # Loader errors and 404s are never cached.
        try:
            encoded = json.dumps(payload, ensure_ascii=False)
            if len(encoded.encode()) <= 1024 * 1024:
                ttl = max(5, min(300, int(os.environ.get("TLHDD_CACHE_TTL", "60"))))
                client.set(data_key, encoded, ex=ttl + random.randint(0, max(1, ttl // 10)))
        except Exception as exc:
            _failed(exc)
        return payload, "miss"
    finally:
        lock.release()
