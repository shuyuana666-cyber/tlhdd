from __future__ import annotations

from typing import Any
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

VIDEO_MEDIA_EXTS = {".mp4", ".webm"}

def is_video_media_url(value: Any) -> bool:
    return PurePosixPath(urlparse(str(value or "").strip()).path).suffix.lower() in VIDEO_MEDIA_EXTS

def valid_public_image_url(value: Any, required: bool = False) -> str:
    url = str(value or "").strip()
    if not url:
        if required:
            raise ValueError("请填写图片 URL")
        return ""
    parsed = urlparse(url)
    if url.startswith("/uploads/") or url.startswith("/assets/"):
        return url
    if parsed.scheme == "https" and parsed.netloc:
        return url
    raise ValueError("图片 URL 仅支持 /uploads/、/assets/ 或 https://")

def valid_public_media_url(value: Any, required: bool = False, allow_video: bool = False) -> str:
    url = str(value or "").strip()
    if not url:
        if required:
            raise ValueError("请填写图片或视频 URL")
        return ""
    if not is_video_media_url(url):
        return valid_public_image_url(url)
    if not allow_video:
        raise ValueError("这个位置只支持图片")
    parsed = urlparse(url)
    path = unquote(parsed.path)
    segments = path.split("/")
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not path.startswith("/uploads/")
        or any(segment in {".", ".."} for segment in segments)
        or PurePosixPath(path).suffix.lower() not in VIDEO_MEDIA_EXTS
    ):
        raise ValueError("视频 URL 仅支持站内 /uploads/ 下的 mp4 或 webm 文件")
    return url
