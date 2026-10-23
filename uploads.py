from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database import connect
from media_storage import publish_upload

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ADMIN_IMAGE_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ADMIN_VIDEO_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_FORUM_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_FORUM_UPLOAD_DAILY_BYTES = 200 * 1024 * 1024
MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", "24000000"))
ALLOWED_UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORUM_UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm", ".mov"}
ALLOWED_FORUM_UPLOAD_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "video/webm",
    "video/quicktime",
}
PUBLIC_UPLOAD_EXTS = ALLOWED_UPLOAD_EXTS | ALLOWED_FORUM_UPLOAD_EXTS

def parse_multipart_file(
    handler: Any,
    max_bytes: int = MAX_UPLOAD_BYTES,
    label: str = "图片",
) -> tuple[str, bytes, str]:
    content_type = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type or "boundary=" not in content_type:
        raise ValueError("请使用文件上传表单")
    length = int(handler.headers.get("Content-Length", "0"))
    size_mb = max(1, max_bytes // (1024 * 1024))
    if length <= 0 or length > max_bytes + 4096:
        raise ValueError(f"{label}大小不能超过 {size_mb}MB")
    boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode("utf-8")
    raw = handler.rfile.read(length)
    for part in raw.split(b"--" + boundary):
        part = part.strip()
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        header_blob, body = part.split(b"\r\n\r\n", 1)
        headers = header_blob.decode("utf-8", "ignore")
        if "filename=" not in headers:
            continue
        disposition = next((line for line in headers.split("\r\n") if line.lower().startswith("content-disposition")), "")
        content_line = next((line for line in headers.split("\r\n") if line.lower().startswith("content-type")), "")
        filename = ""
        for chunk in disposition.split(";"):
            chunk = chunk.strip()
            if chunk.startswith("filename="):
                filename = chunk.split("=", 1)[1].strip().strip('"')
        file_type = content_line.split(":", 1)[1].strip().lower() if ":" in content_line else ""
        data = body[:-2] if body.endswith(b"\r\n") else body
        if not filename or not data:
            raise ValueError(f"没有读取到{label}文件")
        if len(data) > max_bytes:
            raise ValueError(f"{label}大小不能超过 {size_mb}MB")
        return filename, data, file_type
    raise ValueError(f"没有读取到{label}文件")

def detect_upload_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "video/mp4"
    if data.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm"
    return ""

def save_uploaded_file(handler: Any) -> dict[str, Any]:
    filename, data, file_type = parse_multipart_file(handler)
    return _save_admin_image(filename, data, file_type)

def save_admin_media_file(handler: Any) -> dict[str, Any]:
    filename, data, file_type = parse_multipart_file(
        handler,
        MAX_ADMIN_VIDEO_UPLOAD_BYTES,
        "图片或视频",
    )
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    detected_type = detect_upload_type(data)
    if ext in ALLOWED_UPLOAD_EXTS:
        if len(data) > MAX_ADMIN_IMAGE_UPLOAD_BYTES:
            raise ValueError("单张图片不能超过 20MB")
        return _save_admin_image(filename, data, file_type)
    expected_video_type = {".mp4": "video/mp4", ".webm": "video/webm"}.get(ext)
    if (
        not expected_video_type
        or detected_type != expected_video_type
        or (file_type and file_type != expected_video_type)
    ):
        raise ValueError("仅支持 jpg、png、webp 图片和 mp4、webm 视频")
    today = datetime.now(timezone.utc)
    target_dir = UPLOAD_DIR / today.strftime("%Y") / today.strftime("%m")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{secrets.token_hex(16)}{ext}"
    target = target_dir / target_name
    target.write_bytes(data)
    return publish_upload({
        "url": f"/uploads/{today:%Y}/{today:%m}/{target_name}",
        "media_type": "video",
        "size_bytes": len(data),
        "name": Path(filename).name[:120],
    })

def _save_admin_image(filename: str, data: bytes, file_type: str) -> dict[str, Any]:
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    expected_image_type = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext)
    detected_type = detect_upload_type(data)
    if (
        not expected_image_type
        or detected_type != expected_image_type
        or (file_type and file_type != expected_image_type)
    ):
        raise ValueError("仅支持格式正确的 jpg、png、webp 图片")
    today = datetime.now(timezone.utc)
    target_dir = UPLOAD_DIR / today.strftime("%Y") / today.strftime("%m")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{secrets.token_hex(16)}{ext}"
    target = target_dir / target_name
    target.write_bytes(data)
    result = {
        "url": f"/uploads/{today:%Y}/{today:%m}/{target_name}",
        "media_type": "image",
        "size_bytes": len(data),
    }
    derivatives = create_image_derivatives(target, today, optimized_size=(1920, 1920))
    if not derivatives.get("optimized_url") or not derivatives.get("thumb_url"):
        target.unlink(missing_ok=True)
        target.with_name(f"{target.stem}-optimized.webp").unlink(missing_ok=True)
        target.with_name(f"{target.stem}-thumb.webp").unlink(missing_ok=True)
        raise ValueError("图片压缩失败，请确认服务器已安装 Pillow")
    result.update(derivatives)
    return publish_upload(result)

class UploadQuotaExceeded(ValueError):
    pass

def reserve_forum_upload_quota(user: dict[str, Any], size_bytes: int) -> None:
    user_kind = "admin" if user.get("permission") == "admin" else "public"
    with connect() as conn:
        conn.execute(
            """INSERT IGNORE INTO forum_upload_usage (user_kind, user_id, usage_date, bytes_used)
               VALUES (?, ?, UTC_DATE(), 0)""",
            (user_kind, int(user["id"])),
        )
        result = conn.execute(
            """UPDATE forum_upload_usage
               SET bytes_used=bytes_used + ?, updated_at=UTC_TIMESTAMP()
               WHERE user_kind=? AND user_id=? AND usage_date=UTC_DATE()
                 AND bytes_used + ? <= ?""",
            (size_bytes, user_kind, int(user["id"]), size_bytes, MAX_FORUM_UPLOAD_DAILY_BYTES),
        )
        if result.rowcount != 1:
            raise UploadQuotaExceeded("今天的论坛上传额度已用完，请明天再上传")

def release_forum_upload_quota(user: dict[str, Any], size_bytes: int) -> None:
    user_kind = "admin" if user.get("permission") == "admin" else "public"
    with connect() as conn:
        conn.execute(
            """UPDATE forum_upload_usage
               SET bytes_used=GREATEST(bytes_used - ?, 0), updated_at=UTC_TIMESTAMP()
               WHERE user_kind=? AND user_id=? AND usage_date=UTC_DATE()""",
            (size_bytes, user_kind, int(user["id"])),
        )

def save_forum_media_file(handler: Any, user: dict[str, Any]) -> dict[str, str]:
    filename, data, file_type = parse_multipart_file(handler, MAX_FORUM_UPLOAD_BYTES, "文件")
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    detected_type = detect_upload_type(data)
    if ext not in ALLOWED_FORUM_UPLOAD_EXTS or (file_type and file_type not in ALLOWED_FORUM_UPLOAD_TYPES) or detected_type not in ALLOWED_FORUM_UPLOAD_TYPES:
        raise ValueError("仅支持 jpg、png、webp 图片和 mp4、webm、mov 视频")
    kind = "video" if ext in {".mp4", ".webm", ".mov"} or detected_type.startswith("video/") else "image"
    quota_bytes = len(data)
    reserve_forum_upload_quota(user, quota_bytes)
    today = datetime.now(timezone.utc)
    target_dir = UPLOAD_DIR / today.strftime("%Y") / today.strftime("%m")
    target_name = f"{secrets.token_hex(16)}{ext}"
    target = target_dir / target_name
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        result = {
            "url": f"/uploads/{today:%Y}/{today:%m}/{target_name}",
            "type": kind,
            "name": Path(filename).name[:120],
        }
        if kind == "image":
            derivatives = create_image_derivatives(target, today)
            if not derivatives.get("optimized_url") or not derivatives.get("thumb_url"):
                raise ValueError("图片压缩失败，请确认服务器已安装 Pillow")
            result.update(derivatives)
        return publish_upload(result)
    except Exception:
        target.unlink(missing_ok=True)
        target.with_name(f"{target.stem}-optimized.webp").unlink(missing_ok=True)
        target.with_name(f"{target.stem}-thumb.webp").unlink(missing_ok=True)
        release_forum_upload_quota(user, quota_bytes)
        raise

def create_image_derivatives(
    source: Path,
    today: datetime,
    optimized_size: tuple[int, int] = (1400, 1400),
) -> dict[str, str]:
    try:
        from PIL import Image, ImageOps
    except Exception:
        return {}
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                return {}
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            base = source.stem
            output: dict[str, str] = {}
            for suffix, max_size, quality in (("optimized", optimized_size, 82), ("thumb", (640, 480), 76)):
                copy = image.copy()
                copy.thumbnail(max_size)
                if copy.mode == "RGBA":
                    background = Image.new("RGB", copy.size, (255, 255, 255))
                    background.paste(copy, mask=copy.split()[-1])
                    copy = background
                target = source.with_name(f"{base}-{suffix}.webp")
                copy.save(target, "WEBP", quality=quality, method=6)
                output[f"{suffix}_url"] = f"/uploads/{today:%Y}/{today:%m}/{target.name}"
            return output
    except Exception:
        return {}
