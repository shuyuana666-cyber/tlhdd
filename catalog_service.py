"""Catalog queries, validation, and persistence for vehicles and parts."""

from __future__ import annotations

import json
import re
import secrets
from typing import Any

from content_defaults import DEFAULT_CATALOG_TERMS, PART_CATEGORIES, PART_CATEGORY_DEFAULT
from database import DatabaseConnection, IntegrityError, connect
from record_utils import normalize_record, normalize_records, row_to_dict, to_bool
from repositories import list_records

CATALOG_SCOPES = {"new_vehicle", "part"}
CATALOG_TERM_TYPES = {"category", "tag"}

def clean_term_key(value: Any, fallback_prefix: str = "term") -> str:
    text = str(value or "").strip().lower().replace(" ", "-")
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in {"-", "_"})
    return cleaned[:64] or f"{fallback_prefix}_{secrets.token_hex(4)}"

def json_list(value: Any, limit: int = 12) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            raw_items = parsed if isinstance(parsed, list) else [text]
        except json.JSONDecodeError:
            raw_items = [item.strip() for item in text.replace("\n", ",").split(",")]
    else:
        raw_items = []
    seen: set[str] = set()
    items: list[str] = []
    for item in raw_items:
        key = clean_term_key(item, "tag")
        if key and key not in seen:
            seen.add(key)
            items.append(key)
        if len(items) >= limit:
            break
    return items

def ensure_default_catalog_terms(conn: DatabaseConnection) -> None:
    marker = "migration.catalog_terms_defaults_seeded"
    if conn.execute("SELECT 1 FROM site_settings WHERE `key`=?", (marker,)).fetchone():
        return
    for term in DEFAULT_CATALOG_TERMS:
        payload = {
            "description_zh": "",
            "description_en": "",
            "description_ru": "",
            "icon": "",
            "is_active": 1,
            **term,
        }
        conn.execute(
            """
            INSERT INTO catalog_terms
            (scope, term_type, term_key, label_zh, label_en, label_ru,
             description_zh, description_en, description_ru, icon, sort_order, is_system, is_active)
            VALUES
            (:scope, :term_type, :term_key, :label_zh, :label_en, :label_ru,
             :description_zh, :description_en, :description_ru, :icon, :sort_order, :is_system, :is_active)
            ON DUPLICATE KEY UPDATE
              is_system=GREATEST(is_system, 1)
            """,
            payload,
        )
    conn.execute(
        "INSERT IGNORE INTO site_settings (`key`, `value`) VALUES (?, '1')",
        (marker,),
    )

def infer_new_catalog_key(category_text: str) -> str:
    text = category_text.lower()
    if "suv" in text or "越野" in text:
        return "suv"
    if "轿" in text or "sedan" in text or "сeдан" in text or "седан" in text:
        return "sedan"
    if "新能源" in text or "ev" in text or "hybrid" in text or "混动" in text or "электро" in text or "гибрид" in text:
        return "ev"
    if "批量" in text or "bulk" in text or "dealer" in text or "опт" in text:
        return "bulk"
    return ""

def infer_vehicle_year(title: Any) -> str:
    match = re.search(r"\b(19[8-9]\d|20[0-4]\d)\b", str(title or ""))
    return match.group(1) if match else ""

def backfill_catalog_keys(conn: DatabaseConnection) -> None:
    rows = conn.execute(
        """
        SELECT id, category_zh, category_en, category_ru, catalog_category_key
        FROM vehicles
        WHERE vehicle_type='new'
        """
    ).fetchall()
    for row in rows:
        if row["catalog_category_key"]:
            continue
        key = infer_new_catalog_key(" ".join(str(row[col] or "") for col in ("category_zh", "category_en", "category_ru")))
        if key:
            conn.execute("UPDATE vehicles SET catalog_category_key=? WHERE id=?", (key, row["id"]))

def backfill_vehicle_years(conn: DatabaseConnection) -> None:
    rows = conn.execute(
        """
        SELECT id, title, model_year
        FROM vehicles
        WHERE model_year=''
        """
    ).fetchall()
    for row in rows:
        year = infer_vehicle_year(row["title"])
        if year:
            conn.execute("UPDATE vehicles SET model_year=? WHERE id=?", (year, row["id"]))

def list_catalog_terms(scope: str = "", term_type: str = "", admin: bool = False) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if scope in CATALOG_SCOPES:
        clauses.append("scope=?")
        params.append(scope)
    if term_type in CATALOG_TERM_TYPES:
        clauses.append("term_type=?")
        params.append(term_type)
    if not admin:
        clauses.append("is_active=1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, scope, term_type, term_key, label_zh, label_en, label_ru,
                   description_zh, description_en, description_ru, icon, sort_order,
                   is_system, is_active, updated_at
            FROM catalog_terms
            {where}
            ORDER BY scope ASC, term_type ASC, sort_order ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_dict(row) for row in rows]

def get_catalog_term(scope: str, term_type: str, term_key: str, admin: bool = True) -> dict[str, Any] | None:
    if scope not in CATALOG_SCOPES or term_type not in CATALOG_TERM_TYPES or not term_key:
        return None
    clauses = "scope=? AND term_type=? AND term_key=?"
    params: list[Any] = [scope, term_type, term_key]
    if not admin:
        clauses += " AND is_active=1"
    with connect() as conn:
        row = conn.execute(f"SELECT * FROM catalog_terms WHERE {clauses}", tuple(params)).fetchone()
    return row_to_dict(row) if row else None

def catalog_label_tuple(scope: str, key: str) -> tuple[str, str, str]:
    term = get_catalog_term(scope, "category", key, admin=True)
    if term:
        return str(term.get("label_zh", "")), str(term.get("label_en", "")), str(term.get("label_ru", ""))
    if scope == "part" and key in PART_CATEGORIES:
        return PART_CATEGORIES[key]
    return "", "", ""

def valid_catalog_key(scope: str, term_type: str, key: str, allow_all: bool = False) -> bool:
    if not key:
        return False
    if key == "all" and allow_all:
        return True
    if key == "all":
        return False
    return get_catalog_term(scope, term_type, key, admin=True) is not None

def sanitize_catalog_tags(scope: str, value: Any) -> list[str]:
    keys = json_list(value, limit=10)
    if not keys:
        return []
    valid = {term["term_key"] for term in list_catalog_terms(scope, "tag", admin=True)}
    return [key for key in keys if key in valid]

def get_catalog_term_by_id(term_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalog_terms WHERE id=?", (term_id,)).fetchone()
    if not row:
        raise ValueError("分类标签不存在")
    return row_to_dict(row)

def prepare_catalog_term_fields(data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    scope = str(data.get("scope", current.get("scope", ""))).strip()
    term_type = str(data.get("term_type", current.get("term_type", ""))).strip()
    if scope not in CATALOG_SCOPES:
        raise ValueError("请选择分类标签适用范围")
    if term_type not in CATALOG_TERM_TYPES:
        raise ValueError("请选择分类或标签")
    term_key = clean_term_key(data.get("term_key", current.get("term_key", "")), term_type)
    if current.get("is_system"):
        term_key = str(current.get("term_key", term_key))
        scope = str(current.get("scope", scope))
        term_type = str(current.get("term_type", term_type))
    label_zh = str(data.get("label_zh", current.get("label_zh", ""))).strip()
    label_en = str(data.get("label_en", current.get("label_en", ""))).strip()
    label_ru = str(data.get("label_ru", current.get("label_ru", ""))).strip()
    if not any((label_zh, label_en, label_ru)):
        raise ValueError("请至少填写一个显示名称")
    fields = {
        "scope": scope,
        "term_type": term_type,
        "term_key": term_key,
        "label_zh": label_zh or label_en or label_ru or term_key,
        "label_en": label_en or label_zh or label_ru or term_key,
        "label_ru": label_ru or label_zh or label_en or term_key,
        "description_zh": str(data.get("description_zh", current.get("description_zh", ""))).strip(),
        "description_en": str(data.get("description_en", current.get("description_en", ""))).strip(),
        "description_ru": str(data.get("description_ru", current.get("description_ru", ""))).strip(),
        "icon": str(data.get("icon", current.get("icon", ""))).strip()[:80],
        "sort_order": int(data.get("sort_order", current.get("sort_order", 0)) or 0),
        "is_system": 1 if current.get("is_system") or term_key == "all" else to_bool(data.get("is_system", False)),
        "is_active": 1 if term_key == "all" else to_bool(data.get("is_active", current.get("is_active", True))),
    }
    return fields

def save_catalog_term(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    current = get_catalog_term_by_id(item_id) if item_id else {}
    fields = prepare_catalog_term_fields(data, current)
    try:
        with connect() as conn:
            if item_id:
                fields["id"] = item_id
                conn.execute(
                    """
                    UPDATE catalog_terms
                    SET scope=:scope, term_type=:term_type, term_key=:term_key,
                        label_zh=:label_zh, label_en=:label_en, label_ru=:label_ru,
                        description_zh=:description_zh, description_en=:description_en,
                        description_ru=:description_ru, icon=:icon, sort_order=:sort_order,
                        is_system=:is_system, is_active=:is_active, updated_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                    """,
                    fields,
                )
                new_id = item_id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO catalog_terms
                    (scope, term_type, term_key, label_zh, label_en, label_ru,
                     description_zh, description_en, description_ru, icon, sort_order,
                     is_system, is_active)
                    VALUES
                    (:scope, :term_type, :term_key, :label_zh, :label_en, :label_ru,
                     :description_zh, :description_en, :description_ru, :icon, :sort_order,
                     :is_system, :is_active)
                    """,
                    fields,
                )
                new_id = int(cur.lastrowid)
    except IntegrityError as exc:
        raise ValueError("同一范围下的分类/标签标识不能重复") from exc
    return get_catalog_term_by_id(int(new_id))

def search_vehicles(query: str = "", vehicle_type: str = "") -> list[dict[str, Any]]:
    query = f"%{query.strip()}%"
    clauses = ["is_active=1"]
    params: list[Any] = []
    if vehicle_type in {"new", "used"}:
        clauses.append("vehicle_type=?")
        params.append(vehicle_type)
    if query != "%%":
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR model LIKE ? OR engine LIKE ? OR mileage LIKE ?
             OR category_zh LIKE ? OR category_en LIKE ? OR category_ru LIKE ?
             OR description_zh LIKE ? OR description_en LIKE ? OR description_ru LIKE ?)
            """
        )
        params.extend([query] * 11)
    where = "WHERE " + " AND ".join(clauses)
    return list_records("vehicles", where, tuple(params))

def global_search(query: str) -> dict[str, list[dict[str, Any]]]:
    query = str(query or "").strip()[:120]
    if not query:
        return {"vehicles": [], "parts": []}
    like = f"%{query}%"
    vehicle_columns = (
        "title", "brand", "model", "model_year", "engine", "mileage", "price",
        "category_zh", "category_en", "category_ru", "catalog_category_key", "tag_keys_json",
        "description_zh", "description_en", "description_ru",
    )
    part_columns = (
        "title", "category_key", "category_zh", "category_en", "category_ru", "tag_keys_json",
        "brand", "part_no", "compatible_models", "price", "description_zh", "description_en", "description_ru",
    )
    vehicle_where = " OR ".join(f"{column} LIKE ?" for column in vehicle_columns)
    part_where = " OR ".join(f"{column} LIKE ?" for column in part_columns)
    with connect() as conn:
        vehicles = conn.execute(
            f"SELECT * FROM vehicles WHERE is_active=1 AND ({vehicle_where}) ORDER BY is_featured DESC, sort_order ASC, id DESC LIMIT 12",
            (like,) * len(vehicle_columns),
        ).fetchall()
        parts = conn.execute(
            f"SELECT * FROM parts WHERE is_active=1 AND ({part_where}) ORDER BY is_featured DESC, sort_order ASC, id DESC LIMIT 12",
            (like,) * len(part_columns),
        ).fetchall()
    return {"vehicles": normalize_records(vehicles), "parts": normalize_records(parts)}

def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))

def public_vehicle_payload(params: dict[str, list[str]]) -> dict[str, Any]:
    vehicle_type = params.get("type", [""])[0]
    page = clamp_int(params.get("page", ["1"])[0], 1, 1, 10_000)
    page_size = clamp_int(params.get("page_size", ["12"])[0], 12, 1, 60)
    category = str(params.get("category", [""])[0]).strip()
    brand = str(params.get("brand", [""])[0]).strip()
    model = str(params.get("model", [""])[0]).strip()
    vehicle_id = str(params.get("id", [""])[0]).strip()
    q = str(params.get("q", [""])[0]).strip()
    clauses = ["is_active=1"]
    sql_params: list[Any] = []
    if vehicle_type in {"new", "used"}:
        clauses.append("vehicle_type=?")
        sql_params.append(vehicle_type)
    if vehicle_id:
        clauses.append("id=?")
        sql_params.append(vehicle_id)
    if category:
        clauses.append("catalog_category_key=?")
        sql_params.append(category)
    if brand:
        clauses.append("brand=?")
        sql_params.append(brand)
    if model:
        clauses.append("model=?")
        sql_params.append(model)
    if q:
        like = f"%{q}%"
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR model LIKE ? OR engine LIKE ? OR mileage LIKE ?
             OR category_zh LIKE ? OR category_en LIKE ? OR category_ru LIKE ?
             OR description_zh LIKE ? OR description_en LIKE ? OR description_ru LIKE ?)
            """
        )
        sql_params.extend([like] * 11)
    where = "WHERE " + " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM vehicles {where}", tuple(sql_params)).fetchone()[0])
        rows = conn.execute(
            f"SELECT * FROM vehicles {where} ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?",
            tuple(sql_params + [page_size, offset]),
        ).fetchall()
    vehicles = normalize_records(rows)
    return {
        "vehicles": vehicles,
        "items": vehicles,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }

def get_public_vehicle(vehicle_id: int, vehicle_type: str = "") -> dict[str, Any]:
    clauses = ["id=?", "is_active=1"]
    params: list[Any] = [vehicle_id]
    if vehicle_type in {"new", "used"}:
        clauses.append("vehicle_type=?")
        params.append(vehicle_type)
    with connect() as conn:
        row = conn.execute(f"SELECT * FROM vehicles WHERE {' AND '.join(clauses)}", tuple(params)).fetchone()
    if not row:
        raise ValueError("车辆不存在")
    return normalize_record(row_to_dict(row))

def public_part_payload(params: dict[str, list[str]]) -> dict[str, Any]:
    page = clamp_int(params.get("page", ["1"])[0], 1, 1, 10_000)
    page_size = clamp_int(params.get("page_size", ["12"])[0], 12, 1, 60)
    category = str(params.get("category", [""])[0]).strip()
    q = str(params.get("q", [""])[0]).strip()
    clauses = ["is_active=1"]
    sql_params: list[Any] = []
    if category:
        clauses.append("category_key=?")
        sql_params.append(category)
    if q:
        like = f"%{q}%"
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR part_no LIKE ? OR compatible_models LIKE ?
             OR category_zh LIKE ? OR category_en LIKE ? OR category_ru LIKE ?
             OR description_zh LIKE ? OR description_en LIKE ? OR description_ru LIKE ?)
            """
        )
        sql_params.extend([like] * 10)
    where = "WHERE " + " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM parts {where}", tuple(sql_params)).fetchone()[0])
        rows = conn.execute(
            f"SELECT * FROM parts {where} ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?",
            tuple(sql_params + [page_size, offset]),
        ).fetchall()
    parts = normalize_records(rows)
    return {
        "parts": parts,
        "items": parts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }

def get_public_part(part_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM parts WHERE id=? AND is_active=1", (part_id,)).fetchone()
    if not row:
        raise ValueError("配件不存在")
    return normalize_record(row_to_dict(row))

def prepare_vehicle_fields(data: dict[str, Any]) -> dict[str, Any]:
    gallery = data.get("gallery", [])
    if isinstance(gallery, str):
        gallery = [line.strip() for line in gallery.splitlines() if line.strip()]
    specs = data.get("specs", {})
    vehicle_type = str(data.get("vehicle_type", "")).strip()
    if vehicle_type not in {"new", "used"}:
        raise ValueError("车辆类型必须为新车或二手车")
    try:
        sort_order = int(data.get("sort_order") or 0)
    except (TypeError, ValueError):
        raise ValueError("排序必须是整数")
    catalog_category_key = ""
    tag_keys = []
    if vehicle_type == "new":
        requested_key = clean_term_key(data.get("catalog_category_key", ""), "category")
        if requested_key and valid_catalog_key("new_vehicle", "category", requested_key):
            catalog_category_key = requested_key
        else:
            catalog_category_key = infer_new_catalog_key(" ".join(str(data.get(key, "")) for key in ("category_zh", "category_en", "category_ru")))
        tag_keys = sanitize_catalog_tags("new_vehicle", data.get("tag_keys") or data.get("tag_keys_json"))
    category_zh = str(data.get("category_zh", "")).strip()
    category_en = str(data.get("category_en", "")).strip()
    category_ru = str(data.get("category_ru", "")).strip()
    if vehicle_type == "new" and catalog_category_key:
        label_zh, label_en, label_ru = catalog_label_tuple("new_vehicle", catalog_category_key)
        category_zh = category_zh or label_zh
        category_en = category_en or label_en
        category_ru = category_ru or label_ru
    fields = {
        "vehicle_type": vehicle_type,
        "title": data.get("title", ""),
        "brand": data.get("brand", ""),
        "model": data.get("model", ""),
        "model_year": str(data.get("model_year", "") or data.get("year", "")).strip()[:20],
        "engine": data.get("engine", ""),
        "mileage": data.get("mileage", ""),
        "price": data.get("price", ""),
        "category_zh": category_zh,
        "category_en": category_en,
        "category_ru": category_ru,
        "catalog_category_key": catalog_category_key,
        "tag_keys_json": json.dumps(tag_keys, ensure_ascii=False),
        "image_url": data.get("image_url", ""),
        "gallery_json": json.dumps(gallery, ensure_ascii=False),
        "description_zh": data.get("description_zh", ""),
        "description_en": data.get("description_en", ""),
        "description_ru": data.get("description_ru", ""),
        "specs_json": json.dumps(specs if isinstance(specs, dict) else {}, ensure_ascii=False),
        "sort_order": sort_order,
        "is_featured": to_bool(data.get("is_featured", False)),
        "is_active": to_bool(data.get("is_active", True)),
    }
    return fields

def save_vehicle(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = prepare_vehicle_fields(data)
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            conn.execute(
                """
                UPDATE vehicles SET vehicle_type=:vehicle_type, title=:title, brand=:brand, model=:model,
                model_year=:model_year, engine=:engine, mileage=:mileage, price=:price, category_zh=:category_zh,
                category_en=:category_en, category_ru=:category_ru, catalog_category_key=:catalog_category_key,
                tag_keys_json=:tag_keys_json, image_url=:image_url, gallery_json=:gallery_json,
                description_zh=:description_zh, description_en=:description_en,
                description_ru=:description_ru, specs_json=:specs_json, sort_order=:sort_order,
                is_featured=:is_featured, is_active=:is_active, updated_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """,
                fields,
            )
            new_id = item_id
        else:
            cur = conn.execute(
                """
                INSERT INTO vehicles
                (vehicle_type, title, brand, model, model_year, engine, mileage, price, category_zh, category_en,
                 category_ru, catalog_category_key, tag_keys_json, image_url, gallery_json,
                 description_zh, description_en, description_ru, specs_json, sort_order,
                 is_featured, is_active)
                VALUES
                (:vehicle_type, :title, :brand, :model, :model_year, :engine, :mileage, :price, :category_zh,
                 :category_en, :category_ru, :catalog_category_key, :tag_keys_json, :image_url,
                 :gallery_json, :description_zh, :description_en, :description_ru, :specs_json,
                 :sort_order, :is_featured, :is_active)
                """,
                fields,
            )
            new_id = int(cur.lastrowid)
    return list_records("vehicles", "WHERE id=?", (new_id,))[0]

def normalize_part_category(value: Any) -> str:
    key = clean_term_key(value, "category")
    if valid_catalog_key("part", "category", key):
        return key
    return PART_CATEGORY_DEFAULT

def prepare_part_fields(data: dict[str, Any]) -> dict[str, Any]:
    gallery = data.get("gallery", [])
    if isinstance(gallery, str):
        gallery = [line.strip() for line in gallery.splitlines() if line.strip()]
    category_key = normalize_part_category(data.get("category_key"))
    category_zh, category_en, category_ru = PART_CATEGORIES.get(category_key, ("", "", ""))
    term_zh, term_en, term_ru = catalog_label_tuple("part", category_key)
    category_zh = term_zh or category_zh
    category_en = term_en or category_en
    category_ru = term_ru or category_ru
    tag_keys = sanitize_catalog_tags("part", data.get("tag_keys") or data.get("tag_keys_json"))
    title = str(data.get("title", "")).strip()
    image_url = str(data.get("image_url", "")).strip()
    if len(title) < 2:
        raise ValueError("配件标题至少 2 个字符")
    if not image_url:
        raise ValueError("请上传或填写配件主图")
    fields = {
        "title": title,
        "category_key": category_key,
        "category_zh": category_zh,
        "category_en": category_en,
        "category_ru": category_ru,
        "tag_keys_json": json.dumps(tag_keys, ensure_ascii=False),
        "brand": data.get("brand", ""),
        "part_no": data.get("part_no", ""),
        "compatible_models": data.get("compatible_models", ""),
        "price": data.get("price", ""),
        "image_url": image_url,
        "gallery_json": json.dumps(gallery, ensure_ascii=False),
        "description_zh": data.get("description_zh", ""),
        "description_en": data.get("description_en", ""),
        "description_ru": data.get("description_ru", ""),
        "sort_order": int(data.get("sort_order") or 0),
        "is_featured": to_bool(data.get("is_featured", False)),
        "is_active": to_bool(data.get("is_active", True)),
    }
    return fields

def save_part(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    fields = prepare_part_fields(data)
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            conn.execute(
                """
                UPDATE parts SET title=:title, category_key=:category_key, category_zh=:category_zh,
                category_en=:category_en, category_ru=:category_ru, tag_keys_json=:tag_keys_json,
                brand=:brand, part_no=:part_no, compatible_models=:compatible_models, price=:price,
                image_url=:image_url, gallery_json=:gallery_json, description_zh=:description_zh,
                description_en=:description_en, description_ru=:description_ru, sort_order=:sort_order,
                is_featured=:is_featured,
                is_active=:is_active, updated_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """,
                fields,
            )
            new_id = item_id
        else:
            cur = conn.execute(
                """
                INSERT INTO parts
                (title, category_key, category_zh, category_en, category_ru, tag_keys_json, brand,
                 part_no, compatible_models, price, image_url, gallery_json, description_zh,
                 description_en, description_ru, sort_order, is_featured, is_active)
                VALUES
                (:title, :category_key, :category_zh, :category_en, :category_ru, :tag_keys_json,
                 :brand, :part_no, :compatible_models, :price, :image_url, :gallery_json,
                 :description_zh, :description_en, :description_ru, :sort_order, :is_featured, :is_active)
                """,
                fields,
            )
            new_id = int(cur.lastrowid)
    return list_records("parts", "WHERE id=?", (new_id,))[0]
