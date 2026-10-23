"""Administrative dashboard and inventory query operations."""

from __future__ import annotations

from typing import Any

from database import connect
from record_utils import normalize_records, row_to_dict

def bulk_delete_inventory(resource: str, ids: Any) -> dict[str, Any]:
    """Delete an explicitly selected inventory batch in one transaction."""
    if resource not in {"vehicles", "parts"}:
        raise ValueError("不支持批量删除此类记录")
    if not isinstance(ids, list) or not 1 <= len(ids) <= 100:
        raise ValueError("请选中 1 至 100 条记录")
    if any(type(item) is not int or not 0 < item <= 2**63 - 1 for item in ids):
        raise ValueError("无效的记录 ID")
    selected = sorted(set(ids))
    placeholders = ",".join("?" for _ in selected)
    with connect() as conn:
        existing = conn.execute(
            f"SELECT id FROM {resource} WHERE id IN ({placeholders}) ORDER BY id FOR UPDATE",
            tuple(selected),
        ).fetchall()
        if len(existing) != len(selected):
            raise ValueError("部分记录不存在或已删除，请刷新列表后重新选择")
        deleted = conn.execute(
            f"DELETE FROM {resource} WHERE id IN ({placeholders})", tuple(selected),
        ).rowcount
        if deleted != len(selected):
            raise ValueError("记录已发生变化，请刷新列表后重试")
    return {"ok": True, "deleted_count": deleted}

def pagination_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {"total": total, "page": min(page, total_pages), "page_size": page_size, "total_pages": total_pages}

def list_admin_vehicles(
    query: str = "",
    vehicle_type: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 12,
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if vehicle_type in {"new", "used"}:
        clauses.append("vehicle_type=?")
        params.append(vehicle_type)
    if status == "active":
        clauses.append("is_active=1")
    elif status == "inactive":
        clauses.append("is_active=0")
    elif status == "featured":
        clauses.append("is_featured=1")
    elif status == "missing_image":
        clauses.append("(image_url IS NULL OR trim(image_url)='')")
    if query.strip():
        term = f"%{query.strip()}%"
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR model LIKE ? OR engine LIKE ? OR mileage LIKE ?
             OR price LIKE ? OR category_zh LIKE ? OR category_en LIKE ? OR category_ru LIKE ?
             OR description_zh LIKE ? OR description_en LIKE ? OR description_ru LIKE ?)
            """
        )
        params.extend([term] * 12)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page - 1) * page_size
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM vehicles {where}", tuple(params)).fetchone()[0])
        meta = pagination_meta(total, page, page_size)
        rows = conn.execute(
            f"""
            SELECT * FROM vehicles
            {where}
            ORDER BY sort_order ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [page_size, (meta["page"] - 1) * page_size if total else offset]),
        ).fetchall()
    return {"items": normalize_records(rows), "pagination": meta}

def list_admin_parts(query: str = "", status: str = "", page: int = 1, page_size: int = 50) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if status == "active":
        clauses.append("is_active=1")
    elif status == "inactive":
        clauses.append("is_active=0")
    elif status == "featured":
        clauses.append("is_featured=1")
    elif status == "missing_image":
        clauses.append("(image_url IS NULL OR trim(image_url)='')")
    if query.strip():
        term = f"%{query.strip()}%"
        clauses.append(
            """
            (title LIKE ? OR brand LIKE ? OR part_no LIKE ? OR compatible_models LIKE ?
             OR category_zh LIKE ? OR category_en LIKE ? OR category_ru LIKE ?
             OR description_zh LIKE ? OR description_en LIKE ? OR description_ru LIKE ?)
            """
        )
        params.extend([term] * 10)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM parts {where}", tuple(params)).fetchone()[0])
        meta = pagination_meta(total, page, page_size)
        rows = conn.execute(
            f"""
            SELECT * FROM parts
            {where}
            ORDER BY sort_order ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [page_size, (meta["page"] - 1) * page_size]),
        ).fetchall()
    return {"items": normalize_records(rows), "pagination": meta}

def admin_dashboard_summary() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM inquiries WHERE status='新询盘') AS new_inquiries,
              (SELECT COUNT(*) FROM chat_threads WHERE status='open' OR admin_unread=1) AS open_messages,
              (SELECT COUNT(*) FROM vehicles) AS total_vehicles,
              (SELECT COUNT(*) FROM vehicles WHERE is_active=1) AS active_vehicles,
              (SELECT COUNT(*) FROM vehicles WHERE is_active=0) AS inactive_vehicles,
              (SELECT COUNT(*) FROM vehicles WHERE is_featured=1) AS featured_vehicles,
              (SELECT COUNT(*) FROM vehicles WHERE image_url IS NULL OR trim(image_url)='') AS missing_vehicle_images,
              (SELECT COUNT(*) FROM parts WHERE is_active=1) AS active_parts,
              (SELECT COUNT(*) FROM hero_slides WHERE is_active=1) AS active_slides
            """
        ).fetchone()
        recent_rows = conn.execute(
            """
            SELECT * FROM vehicles
            ORDER BY updated_at DESC, id DESC
            LIMIT 5
            """
        ).fetchall()
    summary = row_to_dict(row) if row else {}
    summary["recent_vehicles"] = normalize_records(recent_rows)
    return summary
