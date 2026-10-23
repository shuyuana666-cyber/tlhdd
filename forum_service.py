from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from database import DbRow, connect
from record_utils import row_to_dict, to_bool

FORUM_CATEGORIES = {"general", "used", "new", "logistics", "options", "faq"}
FORUM_CATEGORY_DEFAULT = "general"

def normalize_forum_category(value: Any) -> str:
    category = str(value or "").strip().lower()
    return category if category in FORUM_CATEGORIES else FORUM_CATEGORY_DEFAULT

def forum_media_type(url: str, media_type: str = "") -> str:
    kind = str(media_type or "").strip().lower()
    if kind in {"image", "video"}:
        return kind
    ext = Path(urlparse(url).path).suffix.lower()
    return "video" if ext in {".mp4", ".webm", ".mov"} else "image"

def normalize_forum_media(data: Any) -> list[dict[str, str]]:
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    media: list[dict[str, str]] = []
    for item in data[:12]:
        if isinstance(item, str):
            url = item.strip()
            name = Path(urlparse(url).path).name
            kind = forum_media_type(url)
        elif isinstance(item, dict):
            url = str(item.get("url", "")).strip()
            name = str(item.get("name", "")).strip()[:120]
            kind = forum_media_type(url, str(item.get("type", "")))
        else:
            continue
        if not url or not url.startswith("/uploads/"):
            continue
        media.append({"url": url, "type": kind, "name": name or Path(urlparse(url).path).name})
    return media

def forum_post_to_dict(row: DbRow) -> dict[str, Any]:
    item = row_to_dict(row)
    media = normalize_forum_media(item.pop("media_json", "[]"))
    if not media and item.get("image_url"):
        media = [{"url": str(item["image_url"]), "type": forum_media_type(str(item["image_url"])), "name": Path(urlparse(str(item["image_url"])).path).name}]
    item["media"] = media
    return item

def list_forum_posts(query: str = "", category: str = "") -> list[dict[str, Any]]:
    term = f"%{query.strip()}%"
    clauses = []
    params: list[Any] = []
    category_key = normalize_forum_category(category) if category.strip() else ""
    clauses.append("is_active=1")
    clauses.append("moderation_status='approved'")
    if category_key:
        clauses.append("topic_category=?")
        params.append(category_key)
    if query.strip():
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR model LIKE ? OR model_year LIKE ?
             OR content LIKE ? OR author_name LIKE ? OR topic_category LIKE ?)
            """
        )
        params.extend([term] * 7)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, user_kind, user_id, account, author_name, title, brand, model,
                   model_year, image_url, media_json, content, topic_category,
                   is_featured, is_active, moderation_status, admin_note, reviewed_at,
                   created_at, updated_at
            FROM forum_posts
            {where}
            ORDER BY is_featured DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
    return [forum_post_to_dict(row) for row in rows]

def create_forum_post(user: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    title = str(data.get("title", "")).strip()
    brand = str(data.get("brand", "")).strip()
    model = str(data.get("model", "")).strip()
    model_year = str(data.get("model_year", "") or data.get("year", "")).strip()
    image_url = str(data.get("image_url", "")).strip()
    content = str(data.get("content", "")).strip()
    topic_category = normalize_forum_category(data.get("topic_category"))
    media = normalize_forum_media(data.get("media") if "media" in data else data.get("media_json"))
    if not image_url:
        first_image = next((item for item in media if item["type"] == "image"), None)
        if first_image:
            image_url = first_image["url"]
    if len(title) < 2:
        raise ValueError("帖子标题至少 2 个字符")
    if len(content) < 8:
        raise ValueError("车型内容至少 8 个字符")
    account = str(user.get("account") or user.get("username") or "")
    author_name = str(user.get("display_name") or account or "用户")
    is_admin = user.get("permission") == "admin"
    is_featured = to_bool(data.get("is_featured", False)) if is_admin else 0
    moderation_status = "approved" if is_admin else "pending"
    reviewed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") if is_admin else None
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO forum_posts
            (user_kind, user_id, account, author_name, title, brand, model, model_year,
             image_url, media_json, content, topic_category, is_featured, moderation_status, reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "admin" if is_admin else "public",
                int(user["id"]),
                account,
                author_name,
                title,
                brand,
                model,
                model_year,
                image_url,
                json.dumps(media, ensure_ascii=False),
                content,
                topic_category,
                is_featured,
                moderation_status,
                reviewed_at,
            ),
        )
        post_id = int(cur.lastrowid)
    return list_forum_posts_by_id(post_id)

def list_forum_posts_by_id(post_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, user_kind, user_id, account, author_name, title, brand, model,
                   model_year, image_url, media_json, content, topic_category,
                   is_featured, is_active, moderation_status, admin_note, reviewed_at,
                   created_at, updated_at
            FROM forum_posts
            WHERE id=?
            """,
            (post_id,),
        ).fetchone()
    if not row:
        raise ValueError("帖子不存在")
    return forum_post_to_dict(row)

def get_public_forum_post(post_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, user_kind, user_id, account, author_name, title, brand, model,
                   model_year, image_url, media_json, content, topic_category,
                   is_featured, is_active, moderation_status, admin_note, reviewed_at,
                   created_at, updated_at
            FROM forum_posts
            WHERE id=? AND is_active=1 AND moderation_status='approved'
            """,
            (post_id,),
        ).fetchone()
    if not row:
        raise ValueError("帖子不存在")
    return forum_post_to_dict(row)

def list_user_forum_posts(user_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_kind, user_id, account, author_name, title, brand, model,
                   model_year, image_url, media_json, content, topic_category,
                   is_featured, is_active, moderation_status, admin_note, reviewed_at,
                   created_at, updated_at
            FROM forum_posts
            WHERE user_kind='public' AND user_id=?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [forum_post_to_dict(row) for row in rows]
