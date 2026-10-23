from __future__ import annotations

from typing import Any

from app_config import RETIRED_PAGE_KEYS
from content_defaults import PAGE_MEDIA_DEFAULTS, SETTING_DEFAULTS
from database import IntegrityError, connect
from record_utils import row_to_dict, to_bool, with_image_variants
from repositories import list_records
from url_utils import is_video_media_url, valid_public_media_url

def get_settings() -> dict[str, str]:
    with connect() as conn:
        rows = conn.execute("SELECT `key`, `value` FROM site_settings").fetchall()
    settings = dict(SETTING_DEFAULTS)
    settings.update({row["key"]: row["value"] for row in rows if not str(row["key"]).startswith("migration.")})
    return settings

def save_settings(data: dict[str, Any]) -> dict[str, str]:
    allowed = set(SETTING_DEFAULTS)
    with connect() as conn:
        for key, value in data.items():
            if key not in allowed:
                continue
            conn.execute(
                """
                INSERT INTO site_settings (`key`, `value`, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE `value`=?, updated_at=CURRENT_TIMESTAMP
                """,
                (key, str(value).strip(), str(value).strip()),
            )
    return get_settings()

def list_page_media(page_key: str = "") -> list[dict[str, Any]]:
    clauses = ["page_key NOT IN (?, ?, ?)"]
    params: list[Any] = list(RETIRED_PAGE_KEYS)
    if page_key:
        clauses.append("page_key=?")
        params.append(page_key)
    where = f"WHERE {' AND '.join(clauses)}"
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, page_key, media_key, label, group_label, image_url, default_url,
                   keep_original, sort_order, is_active, updated_at
            FROM page_media
            {where}
            ORDER BY page_key ASC, sort_order ASC, id ASC
            """,
            params,
        ).fetchall()
    guidance = {
        (item["page_key"], item["media_key"]): item
        for item in PAGE_MEDIA_DEFAULTS
    }
    items = [row_to_dict(row) for row in rows]
    for item in items:
        item["keep_original"] = bool(item.get("keep_original"))
        item["is_active"] = bool(item.get("is_active"))
        item.update({
            key: value
            for key, value in guidance.get((item["page_key"], item["media_key"]), {}).items()
            if key not in {"page_key", "media_key", "image_url", "default_url", "sort_order", "keep_original"}
        })
        item["media_type"] = "video" if is_video_media_url(item.get("image_url")) else "image"
        with_image_variants(item)
    return items

def get_page_media(item_id: int) -> dict[str, Any]:
    item = next((item for item in list_page_media() if int(item["id"]) == int(item_id)), None)
    if not item:
        raise ValueError("页面图片不存在")
    return item

def save_page_media(data: dict[str, Any], item_id: int) -> dict[str, Any]:
    current = get_page_media(item_id)
    restore = to_bool(data.get("restore", False))
    if restore:
        image_url = str(current.get("default_url", "")).strip()
        is_active = True
    else:
        image_url = str(data.get("image_url", current.get("image_url", ""))).strip()
        if image_url:
            image_url = valid_public_media_url(image_url, allow_video=bool(current.get("allow_video")))
        is_active = to_bool(data.get("is_active", bool(image_url))) and bool(image_url)
    with connect() as conn:
        conn.execute(
            """
            UPDATE page_media
            SET image_url=?, is_active=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (image_url, int(is_active), item_id),
        )
    return get_page_media(item_id)

def remove_page_media(item_id: int) -> dict[str, Any]:
    get_page_media(item_id)
    with connect() as conn:
        cur = conn.execute("DELETE FROM page_media WHERE id=?", (item_id,))
        if cur.rowcount <= 0:
            raise ValueError("页面素材不存在或已删除")
    return {"ok": True}

def list_page_section_items(section_id: int, admin: bool = False) -> list[dict[str, Any]]:
    where = "WHERE section_id=?"
    params: list[Any] = [section_id]
    if not admin:
        where += " AND is_active=1"
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, section_id, title_zh, title_en, title_ru, body_zh, body_en, body_ru,
                   image_url, link_url, sort_order, is_active, updated_at
            FROM page_section_items
            {where}
            ORDER BY sort_order ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_dict(row) for row in rows]

def list_page_sections(page_key: str = "", admin: bool = False) -> list[dict[str, Any]]:
    clauses: list[str] = ["page_key NOT IN (?, ?, ?)"]
    params: list[Any] = list(RETIRED_PAGE_KEYS)
    if page_key:
        clauses.append("page_key=?")
        params.append(page_key)
    if not admin:
        clauses.append("is_active=1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, page_key, section_key, label, eyebrow, title_zh, title_en, title_ru,
                   body_zh, body_en, body_ru, image_url, link_url, link_label_zh,
                   link_label_en, link_label_ru, sort_order, is_active, updated_at
            FROM page_sections
            {where}
            ORDER BY page_key ASC, sort_order ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        # Fetch all child items once, on the same connection as their sections.
        item_rows = []
        if rows:
            ids = [int(row["id"]) for row in rows]
            placeholders = ",".join("?" for _ in ids)
            visible = "" if admin else " AND is_active=1"
            item_rows = conn.execute(
                f"""SELECT id, section_id, title_zh, title_en, title_ru, body_zh, body_en, body_ru,
                           image_url, link_url, sort_order, is_active, updated_at
                    FROM page_section_items WHERE section_id IN ({placeholders}){visible}
                    ORDER BY sort_order ASC, id ASC""", tuple(ids),
            ).fetchall()
    children: dict[int, list[dict[str, Any]]] = {}
    for row in item_rows:
        children.setdefault(int(row["section_id"]), []).append(row_to_dict(row))
    sections = [row_to_dict(row) for row in rows]
    for section in sections:
        section["items"] = children.get(int(section["id"]), [])
    return sections

def get_page_section(section_id: int) -> dict[str, Any]:
    sections = [section for section in list_page_sections(admin=True) if int(section["id"]) == int(section_id)]
    if not sections:
        raise ValueError("页面区块不存在")
    return sections[0]

def prepare_page_section_fields(data: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "page_key": str(data.get("page_key", "")).strip()[:80],
        "section_key": str(data.get("section_key", "")).strip()[:80],
        "label": str(data.get("label", "")).strip()[:120],
        "eyebrow": str(data.get("eyebrow", "")).strip()[:120],
        "title_zh": str(data.get("title_zh", "")).strip(),
        "title_en": str(data.get("title_en", "")).strip(),
        "title_ru": str(data.get("title_ru", "")).strip(),
        "body_zh": str(data.get("body_zh", "")).strip(),
        "body_en": str(data.get("body_en", "")).strip(),
        "body_ru": str(data.get("body_ru", "")).strip(),
        "image_url": str(data.get("image_url", "")).strip(),
        "link_url": str(data.get("link_url", "")).strip(),
        "link_label_zh": str(data.get("link_label_zh", "")).strip(),
        "link_label_en": str(data.get("link_label_en", "")).strip(),
        "link_label_ru": str(data.get("link_label_ru", "")).strip(),
        "sort_order": int(data.get("sort_order") or 0),
        "is_active": to_bool(data.get("is_active", True)),
    }
    if not fields["page_key"] or not fields["section_key"]:
        raise ValueError("请填写页面标识和区块标识")
    if fields["page_key"] in RETIRED_PAGE_KEYS:
        raise ValueError("该页面已下线，不能继续维护页面区块")
    if fields["image_url"]:
        fields["image_url"] = valid_public_media_url(
            fields["image_url"],
            allow_video=fields["section_key"] == "hero",
        )
    if not fields["label"]:
        fields["label"] = f"{fields['page_key']} / {fields['section_key']}"
    return fields

def save_page_section(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = prepare_page_section_fields(data)
    try:
        with connect() as conn:
            if item_id:
                fields["id"] = item_id
                conn.execute(
                    """
                    UPDATE page_sections
                    SET page_key=:page_key, section_key=:section_key, label=:label, eyebrow=:eyebrow,
                        title_zh=:title_zh, title_en=:title_en, title_ru=:title_ru,
                        body_zh=:body_zh, body_en=:body_en, body_ru=:body_ru,
                        image_url=:image_url, link_url=:link_url, link_label_zh=:link_label_zh,
                        link_label_en=:link_label_en, link_label_ru=:link_label_ru,
                        sort_order=:sort_order, is_active=:is_active, updated_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                    """,
                    fields,
                )
                new_id = item_id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO page_sections
                    (page_key, section_key, label, eyebrow, title_zh, title_en, title_ru,
                     body_zh, body_en, body_ru, image_url, link_url, link_label_zh,
                     link_label_en, link_label_ru, sort_order, is_active)
                    VALUES
                    (:page_key, :section_key, :label, :eyebrow, :title_zh, :title_en, :title_ru,
                     :body_zh, :body_en, :body_ru, :image_url, :link_url, :link_label_zh,
                     :link_label_en, :link_label_ru, :sort_order, :is_active)
                    """,
                    fields,
                )
                new_id = int(cur.lastrowid)
    except IntegrityError as exc:
        raise ValueError("同一页面下的区块标识不能重复") from exc
    return get_page_section(int(new_id))

def prepare_page_section_item_fields(data: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "section_id": int(data.get("section_id") or 0),
        "title_zh": str(data.get("title_zh", "")).strip(),
        "title_en": str(data.get("title_en", "")).strip(),
        "title_ru": str(data.get("title_ru", "")).strip(),
        "body_zh": str(data.get("body_zh", "")).strip(),
        "body_en": str(data.get("body_en", "")).strip(),
        "body_ru": str(data.get("body_ru", "")).strip(),
        "image_url": str(data.get("image_url", "")).strip(),
        "link_url": str(data.get("link_url", "")).strip(),
        "sort_order": int(data.get("sort_order") or 0),
        "is_active": to_bool(data.get("is_active", True)),
    }
    return fields

def save_page_section_item(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = prepare_page_section_item_fields(data)
    if fields["section_id"] <= 0:
        raise ValueError("请选择所属页面区块")
    get_page_section(fields["section_id"])
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            conn.execute(
                """
                UPDATE page_section_items
                SET section_id=:section_id, title_zh=:title_zh, title_en=:title_en, title_ru=:title_ru,
                    body_zh=:body_zh, body_en=:body_en, body_ru=:body_ru, image_url=:image_url,
                    link_url=:link_url, sort_order=:sort_order, is_active=:is_active,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """,
                fields,
            )
            new_id = item_id
        else:
            cur = conn.execute(
                """
                INSERT INTO page_section_items
                (section_id, title_zh, title_en, title_ru, body_zh, body_en, body_ru,
                 image_url, link_url, sort_order, is_active)
                VALUES
                (:section_id, :title_zh, :title_en, :title_ru, :body_zh, :body_en, :body_ru,
                 :image_url, :link_url, :sort_order, :is_active)
                """,
                fields,
            )
            new_id = int(cur.lastrowid)
    with connect() as conn:
        row = conn.execute("SELECT * FROM page_section_items WHERE id=?", (new_id,)).fetchone()
    if not row:
        raise ValueError("页面条目不存在")
    return row_to_dict(row)

def save_hero_slide(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = {
        "title_zh": data.get("title_zh", ""),
        "title_en": data.get("title_en", ""),
        "title_ru": data.get("title_ru", ""),
        "lead_zh": data.get("lead_zh", ""),
        "lead_en": data.get("lead_en", ""),
        "lead_ru": data.get("lead_ru", ""),
        "image_url": valid_public_media_url(
            data.get("image_url", ""),
            required=item_id is None,
            allow_video=True,
        ),
        "sort_order": int(data.get("sort_order") or 0),
        "is_active": to_bool(data.get("is_active", True)),
    }
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            conn.execute(
                """
                UPDATE hero_slides SET title_zh=:title_zh, title_en=:title_en, title_ru=:title_ru,
                lead_zh=:lead_zh, lead_en=:lead_en, lead_ru=:lead_ru, image_url=:image_url,
                sort_order=:sort_order, is_active=:is_active, updated_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """,
                fields,
            )
            new_id = item_id
        else:
            cur = conn.execute(
                """
                INSERT INTO hero_slides
                (title_zh, title_en, title_ru, lead_zh, lead_en, lead_ru, image_url, sort_order, is_active)
                VALUES
                (:title_zh, :title_en, :title_ru, :lead_zh, :lead_en, :lead_ru, :image_url, :sort_order, :is_active)
                """,
                fields,
            )
            new_id = int(cur.lastrowid)
    return list_records("hero_slides", "WHERE id=?", (new_id,))[0]

def save_metric(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = {
        "value": data.get("value", ""),
        "label_zh": data.get("label_zh", ""),
        "label_en": data.get("label_en", ""),
        "label_ru": data.get("label_ru", ""),
        "sort_order": int(data.get("sort_order") or 0),
        "is_active": to_bool(data.get("is_active", True)),
    }
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            conn.execute(
                """
                UPDATE home_metrics SET `value`=:value, label_zh=:label_zh, label_en=:label_en,
                label_ru=:label_ru, sort_order=:sort_order, is_active=:is_active,
                updated_at=CURRENT_TIMESTAMP WHERE id=:id
                """,
                fields,
            )
            new_id = item_id
        else:
            cur = conn.execute(
                """
                INSERT INTO home_metrics (`value`, label_zh, label_en, label_ru, sort_order, is_active)
                VALUES (:value, :label_zh, :label_en, :label_ru, :sort_order, :is_active)
                """,
                fields,
            )
            new_id = int(cur.lastrowid)
    return list_records("home_metrics", "WHERE id=?", (new_id,))[0]
