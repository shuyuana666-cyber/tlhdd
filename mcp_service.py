"""MCP tool schemas and catalog operations."""

from __future__ import annotations

import json
from typing import Any

from admin_service import list_admin_parts, list_admin_vehicles
from app_config import TLHDD_MCP_TOKEN
from catalog_service import CATALOG_SCOPES, CATALOG_TERM_TYPES, clamp_int, list_catalog_terms, save_part, save_vehicle
from database import connect
from record_utils import row_to_dict
from repositories import list_records
from url_utils import valid_public_image_url

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "tlhdd_health",
        "description": "检查通利华汽车集团 MCP、数据库和商品统计状态。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "tlhdd_list_catalog_terms",
        "description": "查询车辆和配件的分类/标签，用于上架时选择 category_key、catalog_category_key 和 tag_keys。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "enum": ["", "new_vehicle", "part"]},
                "term_type": {"type": "string", "enum": ["", "category", "tag"]},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_search_parts",
        "description": "按关键词、状态和分页查询后台配件，更新前应先调用以避免重复。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "status": {"type": "string", "enum": ["", "active", "inactive", "featured", "missing_image"]},
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_save_part",
        "description": "新增或按 id 更新配件。新增必须提供 title 和 image_url；不会自动去重。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "category_key": {"type": "string"},
                "tag_keys": {"type": ["array", "string"], "items": {"type": "string"}},
                "brand": {"type": "string"},
                "part_no": {"type": "string"},
                "compatible_models": {"type": "string"},
                "price": {"type": "string"},
                "image_url": {"type": "string"},
                "gallery": {"type": ["array", "string"], "items": {"type": "string"}},
                "description_zh": {"type": "string"},
                "description_en": {"type": "string"},
                "description_ru": {"type": "string"},
                "sort_order": {"type": "integer"},
                "is_featured": {"type": "boolean"},
                "is_active": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_get_part",
        "description": "按 id 获取后台配件详情。",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_search_vehicles",
        "description": "按关键词、车型类型、状态和分页查询后台车辆，更新前应先调用以避免重复。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "vehicle_type": {"type": "string", "enum": ["", "new", "used"]},
                "status": {"type": "string", "enum": ["", "active", "inactive", "featured", "missing_image"]},
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_save_vehicle",
        "description": "新增或按 id 更新新车/二手车。新增必须提供 vehicle_type，取值 new 或 used；不会自动去重。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "vehicle_type": {"type": "string", "enum": ["new", "used"]},
                "title": {"type": "string"},
                "brand": {"type": "string"},
                "model": {"type": "string"},
                "model_year": {"type": "string"},
                "engine": {"type": "string"},
                "mileage": {"type": "string"},
                "price": {"type": "string"},
                "category_zh": {"type": "string"},
                "category_en": {"type": "string"},
                "category_ru": {"type": "string"},
                "catalog_category_key": {"type": "string"},
                "tag_keys": {"type": ["array", "string"], "items": {"type": "string"}},
                "image_url": {"type": "string"},
                "gallery": {"type": ["array", "string"], "items": {"type": "string"}},
                "description_zh": {"type": "string"},
                "description_en": {"type": "string"},
                "description_ru": {"type": "string"},
                "specs": {"type": "object"},
                "sort_order": {"type": "integer"},
                "is_featured": {"type": "boolean"},
                "is_active": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tlhdd_get_vehicle",
        "description": "按 id 获取后台车辆详情。",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    },
]

def normalize_mcp_gallery(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [line.strip() for line in value.replace("\n", ",").split(",") if line.strip()]
    elif isinstance(value, list):
        items = [str(item or "").strip() for item in value if str(item or "").strip()]
    else:
        items = []
    return [valid_public_image_url(item) for item in items[:24]]

def mcp_public_url(path: str, resource_id: Any) -> str:
    return f"/{path}?id={resource_id}"

def mcp_health() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM vehicles) AS total_vehicles,
              (SELECT COUNT(*) FROM vehicles WHERE is_active=1) AS active_vehicles,
              (SELECT COUNT(*) FROM parts) AS total_parts,
              (SELECT COUNT(*) FROM parts WHERE is_active=1) AS active_parts
            """
        ).fetchone()
    return {
        "ok": True,
        "database": "ok",
        "mcp_enabled": bool(TLHDD_MCP_TOKEN),
        "counts": row_to_dict(row) if row else {},
    }

def mcp_tool_response(payload: Any) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ],
        "structuredContent": payload,
    }

def mcp_tool_error(message: str) -> dict[str, Any]:
    return {
        "isError": True,
        "content": [{"type": "text", "text": message}],
    }

def mcp_list_catalog_terms(arguments: dict[str, Any]) -> dict[str, Any]:
    scope = str(arguments.get("scope", "")).strip()
    term_type = str(arguments.get("term_type", "")).strip()
    return {
        "terms": list_catalog_terms(scope if scope in CATALOG_SCOPES else "", term_type if term_type in CATALOG_TERM_TYPES else "", admin=True)
    }

def mcp_search_parts(arguments: dict[str, Any]) -> dict[str, Any]:
    page = clamp_int(arguments.get("page"), 1, 1, 100000)
    page_size = clamp_int(arguments.get("page_size"), 20, 1, 100)
    payload = list_admin_parts(
        str(arguments.get("q", "")).strip(),
        str(arguments.get("status", "")).strip(),
        page,
        page_size,
    )
    return {"parts": payload["items"], "pagination": payload["pagination"]}

def mcp_get_record(table: str, item_id: Any, label: str) -> dict[str, Any]:
    try:
        resource_id = int(item_id)
    except (TypeError, ValueError):
        raise ValueError("无效的 ID")
    records = list_records(table, "WHERE id=?", (resource_id,))
    if not records:
        raise ValueError(f"{label}不存在")
    return records[0]

def mcp_optional_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("无效的 ID")

def mcp_save_part(arguments: dict[str, Any]) -> dict[str, Any]:
    data = dict(arguments)
    item_id = mcp_optional_id(data.pop("id", None))
    if item_id is not None:
        data = {**mcp_get_record("parts", item_id, "配件"), **data}
    data["image_url"] = valid_public_image_url(data.get("image_url"), required=True)
    if "gallery" in data:
        data["gallery"] = normalize_mcp_gallery(data.get("gallery"))
    part = save_part(data, item_id)
    return {"part": part, "public_path": mcp_public_url("part-detail.html", part.get("id"))}

def mcp_search_vehicles(arguments: dict[str, Any]) -> dict[str, Any]:
    page = clamp_int(arguments.get("page"), 1, 1, 100000)
    page_size = clamp_int(arguments.get("page_size"), 20, 1, 100)
    payload = list_admin_vehicles(
        str(arguments.get("q", "")).strip(),
        str(arguments.get("vehicle_type", "")).strip(),
        str(arguments.get("status", "")).strip(),
        page,
        page_size,
    )
    return {"vehicles": payload["items"], "pagination": payload["pagination"]}

def mcp_save_vehicle(arguments: dict[str, Any]) -> dict[str, Any]:
    data = dict(arguments)
    item_id = mcp_optional_id(data.pop("id", None))
    if item_id is not None:
        data = {**mcp_get_record("vehicles", item_id, "车辆"), **data}
    if "image_url" in data:
        data["image_url"] = valid_public_image_url(data.get("image_url"))
    if "gallery" in data:
        data["gallery"] = normalize_mcp_gallery(data.get("gallery"))
    vehicle = save_vehicle(data, item_id)
    detail_path = "used-car-detail.html" if vehicle.get("vehicle_type") == "used" else "new-car-detail.html"
    return {"vehicle": vehicle, "public_path": mcp_public_url(detail_path, vehicle.get("id"))}

def mcp_call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "tlhdd_health":
        return mcp_tool_response(mcp_health())
    if name == "tlhdd_list_catalog_terms":
        return mcp_tool_response(mcp_list_catalog_terms(arguments))
    if name == "tlhdd_search_parts":
        return mcp_tool_response(mcp_search_parts(arguments))
    if name == "tlhdd_save_part":
        return mcp_tool_response(mcp_save_part(arguments))
    if name == "tlhdd_get_part":
        return mcp_tool_response({"part": mcp_get_record("parts", arguments.get("id"), "配件")})
    if name == "tlhdd_search_vehicles":
        return mcp_tool_response(mcp_search_vehicles(arguments))
    if name == "tlhdd_save_vehicle":
        return mcp_tool_response(mcp_save_vehicle(arguments))
    if name == "tlhdd_get_vehicle":
        return mcp_tool_response({"vehicle": mcp_get_record("vehicles", arguments.get("id"), "车辆")})
    raise ValueError(f"未知 MCP 工具：{name}")
