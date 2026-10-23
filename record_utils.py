from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from database import DbRow

def with_image_variants(item: dict[str, Any]) -> dict[str, Any]:
    """Expose existing derivatives while retaining the editable source URL."""
    url = str(item.get("image_url") or "")
    path = urlparse(url)
    if path.scheme or path.netloc or not path.path.startswith("/uploads/"):
        return item
    root = Path(__file__).resolve().parent
    uploads = (root / "uploads").resolve()
    source = (root / path.path.lstrip("/")).resolve()
    if not source.is_relative_to(uploads) or not source.is_file() or source.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return item
    stem = source.stem.removesuffix("-optimized").removesuffix("-thumb")
    for suffix in ("optimized", "thumb"):
        candidate = source.with_name(f"{stem}-{suffix}.webp")
        if candidate.is_file() and (suffix == "thumb" or candidate.stat().st_size < source.stat().st_size):
            item[f"{suffix}_url"] = "/" + candidate.relative_to(root).as_posix()
    return item

def to_bool(value: Any) -> int:
    return 1 if str(value).lower() in {"1", "true", "yes", "on"} else 0

def row_to_dict(row: DbRow) -> dict[str, Any]:
    item = dict(row)
    for key, value in item.items():
        if isinstance(value, datetime):
            item[key] = value.isoformat(sep=" ")
    for key in ("is_active", "is_featured", "is_system", "is_read", "admin_unread", "user_unread"):
        if key in item:
            item[key] = bool(item[key])
    return item

def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    if "gallery_json" in item:
        try:
            item["gallery"] = json.loads(item.pop("gallery_json") or "[]")
        except json.JSONDecodeError:
            item["gallery"] = []
    if "specs_json" in item:
        try:
            item["specs"] = json.loads(item.pop("specs_json") or "{}")
        except json.JSONDecodeError:
            item["specs"] = {}
    if "tag_keys_json" in item:
        try:
            item["tag_keys"] = json.loads(item.pop("tag_keys_json") or "[]")
        except json.JSONDecodeError:
            item["tag_keys"] = []
    return item

def normalize_records(rows: list[DbRow]) -> list[dict[str, Any]]:
    return [normalize_record(row_to_dict(row)) for row in rows]
