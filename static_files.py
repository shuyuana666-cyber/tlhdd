from __future__ import annotations

import posixpath
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote

from app_config import BLOCKED_STATIC_DIRS, BLOCKED_STATIC_EXTS, PUBLIC_ROOT_FILES, PUBLIC_STATIC_DIRS
from uploads import PUBLIC_UPLOAD_EXTS

def normalize_static_request_path(url_path: str) -> str:
    decoded = unquote(url_path).replace("\\", "/")
    normalized = posixpath.normpath(decoded)
    if normalized in {".", "/"}:
        return "index.html"
    if normalized.startswith("../") or normalized == "..":
        return ""
    return normalized.lstrip("/")

def static_access_status(url_path: str) -> HTTPStatus | None:
    rel_path = normalize_static_request_path(url_path)
    if not rel_path:
        return HTTPStatus.FORBIDDEN
    if rel_path == "admin":
        return None
    parts = [part for part in rel_path.split("/") if part]
    if not parts:
        return None
    if any(part.startswith(".") for part in parts):
        return HTTPStatus.FORBIDDEN
    first = parts[0]
    if first in BLOCKED_STATIC_DIRS:
        return HTTPStatus.FORBIDDEN
    suffix = Path(rel_path).suffix.lower()
    if suffix in BLOCKED_STATIC_EXTS:
        return HTTPStatus.FORBIDDEN
    if len(parts) == 1:
        return None if rel_path in PUBLIC_ROOT_FILES else HTTPStatus.NOT_FOUND
    if first == "admin":
        admin_rel = "/".join(parts[1:])
        # The bundled Vben build emits hashed JavaScript, CSS, icon and font
        # assets in nested directories under /admin/. Keep source maps and
        # arbitrary files out of the public static surface.
        allowed_admin_exts = {
            ".css",
            ".eot",
            ".gif",
            ".html",
            ".ico",
            ".jpeg",
            ".jpg",
            ".js",
            ".json",
            ".png",
            ".svg",
            ".ttf",
            ".webp",
            ".woff",
            ".woff2",
        }
        allowed_admin_files = {"lucide-local.js", "index.html"}
        if admin_rel in allowed_admin_files:
            return None
        if suffix in allowed_admin_exts and not admin_rel.lower().endswith(".map"):
            return None
        return HTTPStatus.NOT_FOUND
    if first == "uploads":
        if url_path.endswith("/") or suffix not in PUBLIC_UPLOAD_EXTS:
            return HTTPStatus.FORBIDDEN
        return None
    if first in PUBLIC_STATIC_DIRS:
        if url_path.endswith("/"):
            return HTTPStatus.FORBIDDEN
        return None
    return HTTPStatus.NOT_FOUND
