"""MySQL schema initialization and idempotent default-content seeding."""

from __future__ import annotations

import json

from app_config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USER, ENABLE_DEMO_SEED, RETIRED_PAGE_KEYS
from auth_service import MIN_PASSWORD_LENGTH, hash_password
from catalog_service import backfill_catalog_keys, backfill_vehicle_years, ensure_default_catalog_terms
from content_defaults import PAGE_HERO_MEDIA_KEYS, PAGE_MEDIA_DEFAULTS, PAGE_SECTION_DEFAULTS, PAGE_SECTION_ITEM_DEFAULTS, SERVICE_EXPANSION_MEDIA_KEYS, SETTING_DEFAULTS
from database import BASE_DIR, DatabaseConnection, connect, initialize_schema
from demo_seed import ensure_demo_parts

DATA_DIR = BASE_DIR / "data"
REMOVED_DATA_MIGRATION_KEY = "migration.retired-pages-and-forum.v1"


def _unlink_uploaded_urls(urls: list[str]) -> None:
    upload_root = (BASE_DIR / "uploads").resolve()
    for raw_url in urls:
        url = str(raw_url or "").split("?", 1)[0].split("#", 1)[0]
        if not url.startswith("/uploads/"):
            continue
        candidate = (BASE_DIR / url.lstrip("/")).resolve()
        if upload_root not in candidate.parents:
            continue
        candidates = [candidate]
        if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            candidates.extend(
                [
                    candidate.with_name(f"{candidate.stem}-optimized.webp"),
                    candidate.with_name(f"{candidate.stem}-thumb.webp"),
                ]
            )
        for path in candidates:
            path.unlink(missing_ok=True)


def _forum_media_urls(rows: list[dict]) -> list[str]:
    urls: list[str] = []
    for row in rows:
        urls.append(str(row.get("image_url") or ""))
        try:
            media = json.loads(row.get("media_json") or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            media = []
        if not isinstance(media, list):
            continue
        for item in media:
            if not isinstance(item, dict):
                continue
            urls.extend(
                str(item.get(key) or "")
                for key in ("url", "optimized_url", "thumb_url")
            )
    return urls


def purge_removed_data(conn: DatabaseConnection) -> None:
    """Remove retired service-page content and all forum records/media."""
    if conn.execute("SELECT 1 FROM site_settings WHERE `key`=? LIMIT 1", (REMOVED_DATA_MIGRATION_KEY,)).fetchone():
        return
    page_params = RETIRED_PAGE_KEYS
    page_media_rows = conn.execute(
        """
        SELECT image_url, default_url FROM page_media
        WHERE page_key IN (?, ?, ?)
        """,
        page_params,
    ).fetchall()
    section_media_rows = conn.execute(
        """
        SELECT items.image_url
        FROM page_section_items items
        JOIN page_sections sections ON sections.id = items.section_id
        WHERE sections.page_key IN (?, ?, ?)
        """,
        page_params,
    ).fetchall()
    forum_rows = conn.execute("SELECT image_url, media_json FROM forum_posts").fetchall()
    _unlink_uploaded_urls(
        [
            url
            for row in page_media_rows + section_media_rows
            for url in (row.get("image_url"), row.get("default_url"))
        ]
        + _forum_media_urls(forum_rows)
    )

    conn.execute(
        """
        DELETE items FROM page_section_items items
        JOIN page_sections sections ON sections.id = items.section_id
        WHERE sections.page_key IN (?, ?, ?)
        """,
        page_params,
    )
    conn.execute("DELETE FROM page_sections WHERE page_key IN (?, ?, ?)", page_params)
    conn.execute("DELETE FROM page_media WHERE page_key IN (?, ?, ?)", page_params)
    conn.execute("DELETE FROM forum_posts")
    conn.execute("DELETE FROM forum_upload_usage")
    conn.execute(
        "INSERT IGNORE INTO site_settings (`key`, `value`) VALUES (?, ?)",
        (REMOVED_DATA_MIGRATION_KEY, "1"),
    )

def seed_page_defaults(conn: DatabaseConnection) -> None:
    seed_site_settings(conn)
    seeders = (
        ("migration.page_sections_defaults_seeded", seed_page_sections),
        ("migration.page_section_items_defaults_seeded", seed_page_section_items),
        ("migration.page_media_defaults_seeded", seed_page_media),
    )
    for marker, seed in seeders:
        if not _defaults_seeded(conn, marker):
            seed(conn)
            _mark_defaults_seeded(conn, marker)
    expansion_marker = "migration.service_expansion_media.v1"
    if not _defaults_seeded(conn, expansion_marker):
        seed_page_media(conn, SERVICE_EXPANSION_MEDIA_KEYS)
        _mark_defaults_seeded(conn, expansion_marker)
    illustration_marker = "migration.service_option_illustrations.v1"
    if not _defaults_seeded(conn, illustration_marker):
        replace_option_seed_photos(conn)
        _mark_defaults_seeded(conn, illustration_marker)
    service_illustration_marker = "migration.service_page_illustrations.v1"
    if not _defaults_seeded(conn, service_illustration_marker):
        replace_service_seed_photos(conn)
        _mark_defaults_seeded(conn, service_illustration_marker)
    hero_media_marker = "migration.additional_hero_media.v1"
    if not _defaults_seeded(conn, hero_media_marker):
        seed_page_media(conn, PAGE_HERO_MEDIA_KEYS)
        _mark_defaults_seeded(conn, hero_media_marker)
    bundled_media_marker = "migration.bundled_default_media.v1"
    if not _defaults_seeded(conn, bundled_media_marker):
        replace_uploaded_seed_media(conn)
        _mark_defaults_seeded(conn, bundled_media_marker)

def _defaults_seeded(conn: DatabaseConnection, marker: str) -> bool:
    return conn.execute("SELECT 1 FROM site_settings WHERE `key`=?", (marker,)).fetchone() is not None

def _mark_defaults_seeded(conn: DatabaseConnection, marker: str) -> None:
    conn.execute(
        "INSERT IGNORE INTO site_settings (`key`, `value`) VALUES (?, '1')",
        (marker,),
    )

def seed_site_settings(conn: DatabaseConnection) -> None:
    for key, value in SETTING_DEFAULTS.items():
        conn.execute(
            "INSERT IGNORE INTO site_settings (`key`, `value`) VALUES (?, ?)",
            (key, value),
        )

def seed_page_sections(conn: DatabaseConnection) -> None:
    for section in PAGE_SECTION_DEFAULTS:
        conn.execute(
            """
            INSERT IGNORE INTO page_sections
            (page_key, section_key, label, eyebrow, title_zh, title_en, title_ru,
             body_zh, body_en, body_ru, image_url, link_url, link_label_zh,
             link_label_en, link_label_ru, sort_order, is_active)
            VALUES
            (:page_key, :section_key, :label, :eyebrow, :title_zh, :title_en, :title_ru,
             :body_zh, :body_en, :body_ru, :image_url, :link_url, :link_label_zh,
             :link_label_en, :link_label_ru, :sort_order, :is_active)
            """,
            {
                "image_url": "",
                "link_url": "",
                "link_label_zh": "",
                "link_label_en": "",
                "link_label_ru": "",
                "is_active": 1,
                **section,
            },
        )

def seed_page_section_items(conn: DatabaseConnection) -> None:
    for item in PAGE_SECTION_ITEM_DEFAULTS:
        section_row = conn.execute(
            "SELECT id FROM page_sections WHERE page_key=? AND section_key=?",
            (item["page_key"], item["section_key"]),
        ).fetchone()
        if not section_row:
            continue
        exists = conn.execute(
            """
            SELECT id FROM page_section_items
            WHERE section_id=? AND title_zh=? AND sort_order=?
            """,
            (section_row["id"], item["title_zh"], item.get("sort_order", 0)),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO page_section_items
            (section_id, title_zh, title_en, title_ru, body_zh, body_en, body_ru,
             image_url, link_url, sort_order, is_active)
            VALUES
            (:section_id, :title_zh, :title_en, :title_ru, :body_zh, :body_en, :body_ru,
             :image_url, :link_url, :sort_order, :is_active)
            """,
            {
                "section_id": section_row["id"],
                "image_url": item.get("image_url", ""),
                "link_url": item.get("link_url", ""),
                "is_active": 1,
                **{k: v for k, v in item.items() if k not in {"page_key", "section_key"}},
            },
        )

def seed_page_media(conn: DatabaseConnection, media_keys: set[tuple[str, str]] | None = None) -> None:
    for media in PAGE_MEDIA_DEFAULTS:
        if media["page_key"] in RETIRED_PAGE_KEYS:
            continue
        if media_keys is not None and (media["page_key"], media["media_key"]) not in media_keys:
            continue
        conn.execute(
            """
            INSERT IGNORE INTO page_media
            (page_key, media_key, label, group_label, image_url, default_url,
             keep_original, sort_order, is_active)
            VALUES
            (:page_key, :media_key, :label, :group_label, :image_url, :default_url,
             :keep_original, :sort_order, 1)
            """,
            media,
        )


def replace_option_seed_photos(conn: DatabaseConnection) -> None:
    previous_defaults = {
        "snow": "/uploads/2026/06/02bc591169c66934d796a8540184ddf3-optimized.webp",
        "steps": "/uploads/2026/06/48790583e503387714e074635db89e20-optimized.webp",
        "tailgate": "/uploads/2026/06/07a97cf97a1bbd28ce8fce2c9c5532c5-optimized.webp",
        "wrap": "/uploads/2026/06/1d226e629a5efa1a3250f5d63fdafa60-optimized.webp",
    }
    for media in PAGE_MEDIA_DEFAULTS:
        if media["page_key"] != "car-options" or media["media_key"] not in previous_defaults:
            continue
        old_url = previous_defaults[media["media_key"]]
        conn.execute(
            """UPDATE page_media SET image_url=?, default_url=?
               WHERE page_key=? AND media_key=? AND image_url=? AND default_url=?""",
            (media["image_url"], media["default_url"], "car-options", media["media_key"], old_url, old_url),
        )


def replace_service_seed_photos(conn: DatabaseConnection) -> None:
    previous_defaults = {
        ("transportation", "road"): "/uploads/2026/06/024c0f7a350b47b2626664145306d3e1-optimized.webp",
        ("transportation", "sea"): "/uploads/2026/06/48790583e503387714e074635db89e20-optimized.webp",
        ("transportation", "rail"): "/uploads/2026/06/02bc591169c66934d796a8540184ddf3-optimized.webp",
        ("transportation", "tracking"): "/uploads/2026/06/07a97cf97a1bbd28ce8fce2c9c5532c5-optimized.webp",
        ("transportation", "insurance"): "/uploads/2026/06/1d226e629a5efa1a3250f5d63fdafa60-optimized.webp",
        ("purchase-plan", "process"): "/uploads/2026/06/48790583e503387714e074635db89e20-optimized.webp",
        ("service-center", "maintenance"): "/uploads/2026/06/07a97cf97a1bbd28ce8fce2c9c5532c5-optimized.webp",
        ("service-center", "parts"): "/uploads/2026/06/1d226e629a5efa1a3250f5d63fdafa60-optimized.webp",
    }
    for media in PAGE_MEDIA_DEFAULTS:
        key = (media["page_key"], media["media_key"])
        old_url = previous_defaults.get(key)
        if not old_url:
            continue
        conn.execute(
            """UPDATE page_media SET image_url=?, default_url=?
               WHERE page_key=? AND media_key=? AND image_url=? AND default_url=?""",
            (media["image_url"], media["default_url"], *key, old_url, old_url),
        )


def replace_uploaded_seed_media(conn: DatabaseConnection) -> None:
    """Move only original stock media URLs to bundled defaults, keeping edits."""
    asset_prefix = "/assets/default-media/"
    upload_prefix = "/uploads/2026/06/"
    for media in PAGE_MEDIA_DEFAULTS:
        new_url = media["default_url"]
        if not new_url.startswith(asset_prefix):
            continue
        old_url = new_url.replace(asset_prefix, upload_prefix, 1)
        previous_urls = {old_url}
        if old_url.endswith("-optimized.webp"):
            previous_urls.add(old_url[: -len("-optimized.webp")] + ".jpg")
        for previous_url in previous_urls:
            conn.execute(
                """UPDATE page_media SET image_url=?, default_url=?
                   WHERE page_key=? AND media_key=? AND image_url=? AND default_url=?""",
                (new_url, new_url, media["page_key"], media["media_key"], previous_url, previous_url),
            )
            conn.execute(
                """UPDATE page_media SET default_url=?
                   WHERE page_key=? AND media_key=? AND default_url=? AND image_url<>?""",
                (new_url, media["page_key"], media["media_key"], previous_url, previous_url),
            )

def ensure_admin_account(conn: DatabaseConnection) -> None:
    if conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 0:
        if not DEFAULT_ADMIN_PASSWORD:
            raise RuntimeError("TLHDD_ADMIN_PASSWORD must be set before creating the initial admin account")
        conn.execute(
            "INSERT INTO admin_users (username, password_salt, password_hash) VALUES (?, ?, ?)",
            (DEFAULT_ADMIN_USER, *hash_password(DEFAULT_ADMIN_PASSWORD)),
        )

def seed_home_defaults(conn: DatabaseConnection) -> None:
    slides_marker = "migration.home_slides_defaults_seeded"
    if not _defaults_seeded(conn, slides_marker):
        if conn.execute("SELECT COUNT(*) FROM hero_slides").fetchone()[0] == 0:
            slides = [
                (
                    "通利华汽车集团|让车生活更精彩",
                    "Tonglihua Automotive Group|Making Car Life Better",
                    "Автомобильная группа Tonglihua|Делаем автомобильную жизнь ярче",
                    "成立于1994年，通利华汽车集团以汽车服务为核心，覆盖新车销售、售后服务、零配件供应、二手车、汽车进出口、出行与充电服务。",
                    "Founded in 1994, Tonglihua Automotive Group covers new-car sales, after-sales, parts supply, used cars, vehicle import and export, mobility and charging services.",
                    "Основанная в 1994 году группа Tonglihua развивает продажи новых авто, сервис, запчасти, авто с пробегом, импорт и экспорт автомобилей, мобильность и зарядку.",
                    "/assets/images/vehicle-placeholder.webp",
                    1,
                ),
                (
                    "专业服务|覆盖汽车全生命周期",
                    "Professional Service|Across the Vehicle Life Cycle",
                    "Профессиональный сервис|Весь жизненный цикл автомобиля",
                    "从新车销售、售后服务到二手车收购销售、零配件供应和汽车进出口，持续完善汽车生活服务平台。",
                    "From new-car sales and after-sales to used-car acquisition, parts supply and vehicle import and export, we keep improving the automotive service platform.",
                    "От продаж новых авто и сервиса до выкупа авто с пробегом, запчастей и импорта-экспорта мы развиваем единую автомобильную платформу.",
                    "/assets/images/vehicle-placeholder.webp",
                    2,
                ),
                (
                    "开放合作|迈向新时代新通利华",
                    "Open Cooperation|A New Era for Tonglihua",
                    "Открытое сотрудничество|Новая эра Tonglihua",
                    "2016年进入平行进口车业务，2017年取得试点资质，持续拓展二手车出口、出行服务和数字化运营。",
                    "We entered parallel-import vehicles in 2016, gained pilot qualification in 2017 and continue to expand used-car export, mobility and digital operations.",
                    "В 2016 году мы вошли в бизнес параллельного импорта, в 2017 получили статус пилотного предприятия и развиваем экспорт авто с пробегом, мобильность и цифровые сервисы.",
                    "/assets/images/vehicle-placeholder.webp",
                    3,
                ),
            ]
            conn.executemany(
                """
                INSERT INTO hero_slides
                (title_zh, title_en, title_ru, lead_zh, lead_en, lead_ru, image_url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                slides,
            )
        _mark_defaults_seeded(conn, slides_marker)

    metrics_marker = "migration.home_metrics_defaults_seeded"
    if not _defaults_seeded(conn, metrics_marker):
        if conn.execute("SELECT COUNT(*) FROM home_metrics").fetchone()[0] == 0:
            metrics = [
                ("1994", "集团成立年份", "Group founded", "Год основания группы", 1),
                ("5440万", "注册资本（元）", "Registered capital (RMB)", "Уставный капитал (юани)", 2),
                ("40+", "直营服务网络", "Direct service network", "Прямая сеть сервисов", 3),
                ("2000+", "专业服务人才", "Professional employees", "Профессиональные сотрудники", 4),
            ]
            conn.executemany(
                """
                INSERT INTO home_metrics (`value`, label_zh, label_en, label_ru, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                metrics,
            )
        _mark_defaults_seeded(conn, metrics_marker)

def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_ADMIN_PASSWORD and len(DEFAULT_ADMIN_PASSWORD) < MIN_PASSWORD_LENGTH:
        raise RuntimeError(f"TLHDD_ADMIN_PASSWORD must contain at least {MIN_PASSWORD_LENGTH} characters")
    initialize_schema()
    from news_service import seed_news
    seed_news()
    with connect() as conn:
        purge_removed_data(conn)
        ensure_default_catalog_terms(conn)
        backfill_catalog_keys(conn)
        backfill_vehicle_years(conn)
        seed_page_defaults(conn)
        ensure_admin_account(conn)
        conn.execute("DELETE FROM admin_sessions WHERE expires_at <= UTC_TIMESTAMP()")
        conn.execute("DELETE FROM public_sessions WHERE expires_at <= UTC_TIMESTAMP()")
        seed_home_defaults(conn)
        if ENABLE_DEMO_SEED:
            ensure_demo_parts(conn)
        backfill_catalog_keys(conn)
