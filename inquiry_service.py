from __future__ import annotations

from typing import Any

from database import connect
from record_utils import row_to_dict

INQUIRY_STATUSES = {"新询盘", "跟进中", "已报价", "已关闭"}

def create_inquiry(data: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    fields = {
        "user_id": int(user["id"]) if user and user.get("kind") == "public" else None,
        "name": str(data.get("name", "")).strip(),
        "contact": str(data.get("contact", "")).strip(),
        "destination": str(data.get("destination", "")).strip(),
        "vehicle_interest": str(data.get("vehicle_interest") or data.get("service") or "").strip(),
        "budget": str(data.get("budget", "")).strip(),
        "message": str(data.get("message", "")).strip(),
        "source_page": str(data.get("source_page", "")).strip(),
    }
    if len(fields["contact"]) < 3:
        raise ValueError("请填写联系方式")
    if not fields["vehicle_interest"] and not fields["message"]:
        raise ValueError("请填写意向车型或需求说明")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO inquiries
            (user_id, name, contact, destination, vehicle_interest, budget, message, source_page)
            VALUES (:user_id, :name, :contact, :destination, :vehicle_interest, :budget, :message, :source_page)
            """,
            fields,
        )
        inquiry_id = int(cur.lastrowid)
    return get_inquiry(inquiry_id)

def get_inquiry(inquiry_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM inquiries WHERE id=?", (inquiry_id,)).fetchone()
    if not row:
        raise ValueError("询盘不存在")
    return row_to_dict(row)

def list_inquiries(query: str = "", status: str = "") -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status and status in INQUIRY_STATUSES:
        clauses.append("status=?")
        params.append(status)
    if query.strip():
        term = f"%{query.strip()}%"
        clauses.append(
            """
            (name LIKE ? OR contact LIKE ? OR destination LIKE ? OR vehicle_interest LIKE ?
             OR budget LIKE ? OR message LIKE ? OR source_page LIKE ? OR admin_note LIKE ?)
            """
        )
        params.extend([term] * 8)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM inquiries {where} ORDER BY id DESC",
            tuple(params),
        ).fetchall()
    return [row_to_dict(row) for row in rows]

def update_inquiry(inquiry_id: int, data: dict[str, Any]) -> dict[str, Any]:
    status = str(data.get("status", "")).strip()
    if status not in INQUIRY_STATUSES:
        raise ValueError("无效的询盘状态")
    admin_note = str(data.get("admin_note", "")).strip()
    with connect() as conn:
        conn.execute(
            """
            UPDATE inquiries
            SET status=?, admin_note=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, admin_note, inquiry_id),
        )
    return get_inquiry(inquiry_id)

def list_user_inquiries(user_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM inquiries
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]
