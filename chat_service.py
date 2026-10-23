from __future__ import annotations

import secrets
from typing import Any

from database import DbRow, connect
from record_utils import row_to_dict

CHAT_STATUSES = {"open", "follow_up", "closed"}

def chat_thread_to_dict(row: DbRow, include_token: bool = False) -> dict[str, Any]:
    item = row_to_dict(row)
    if not include_token:
        item.pop("guest_token", None)
    return item

def chat_message_to_dict(row: DbRow) -> dict[str, Any]:
    return row_to_dict(row)

def guest_token_from_request(handler: Any) -> str:
    return handler.headers.get("X-Guest-Token", "").strip()

def list_chat_threads(query: str = "", status: str = "", user_id: int | None = None, guest_token: str = "") -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status in CHAT_STATUSES:
        clauses.append("status=?")
        params.append(status)
    if user_id is not None:
        clauses.append("user_id=?")
        params.append(user_id)
    elif guest_token:
        clauses.append("guest_token=?")
        params.append(guest_token)
    if query.strip():
        term = f"%{query.strip()}%"
        clauses.append(
            """
            (contact_name LIKE ? OR contact_info LIKE ? OR product_title LIKE ?
             OR last_message LIKE ? OR product_type LIKE ?)
            """
        )
        params.extend([term] * 5)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM chat_threads
            {where}
            ORDER BY last_message_at DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
    return [chat_thread_to_dict(row) for row in rows]

def delete_chat_thread(thread_id: int) -> dict[str, Any]:
    """Permanently delete a conversation; its messages cascade with the thread."""
    with connect() as conn:
        cur = conn.execute("DELETE FROM chat_threads WHERE id=?", (thread_id,))
        if cur.rowcount <= 0:
            raise ValueError("消息会话不存在或已删除")
    return {"ok": True}

def get_chat_thread_row(thread_id: int) -> DbRow:
    with connect() as conn:
        row = conn.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
    if not row:
        raise ValueError("消息会话不存在")
    return row

def ensure_chat_access(
    thread_id: int,
    user: dict[str, Any] | None = None,
    guest_token: str = "",
    admin: bool = False,
) -> DbRow:
    row = get_chat_thread_row(thread_id)
    if admin or (user and user.get("permission") == "admin"):
        return row
    if user and user.get("kind") == "public" and row["user_id"] and int(row["user_id"]) == int(user["id"]):
        return row
    if guest_token and row["guest_token"] and secrets.compare_digest(str(row["guest_token"]), guest_token):
        return row
    raise PermissionError("无权查看该消息会话")

def list_chat_messages(thread_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, thread_id, sender_kind, sender_name, body, is_read, created_at
            FROM chat_messages
            WHERE thread_id=?
            ORDER BY id ASC
            """,
            (thread_id,),
        ).fetchall()
    return [chat_message_to_dict(row) for row in rows]

def get_chat_thread_payload(thread_id: int, include_token: bool = False, mark_for: str = "") -> dict[str, Any]:
    with connect() as conn:
        if mark_for == "admin":
            conn.execute("UPDATE chat_threads SET admin_unread=0 WHERE id=?", (thread_id,))
            conn.execute("UPDATE chat_messages SET is_read=1 WHERE thread_id=? AND sender_kind IN ('guest', 'user')", (thread_id,))
        elif mark_for == "user":
            conn.execute("UPDATE chat_threads SET user_unread=0 WHERE id=?", (thread_id,))
            conn.execute("UPDATE chat_messages SET is_read=1 WHERE thread_id=? AND sender_kind='admin'", (thread_id,))
        row = conn.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
    if not row:
        raise ValueError("消息会话不存在")
    return {"thread": chat_thread_to_dict(row, include_token=include_token), "messages": list_chat_messages(thread_id)}

def normalize_product_type(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"new_vehicle", "used_vehicle", "part"} else "new_vehicle"

def create_chat_thread(data: dict[str, Any], user: dict[str, Any] | None, guest_token: str = "") -> dict[str, Any]:
    message = str(data.get("message") or data.get("body") or "").strip()
    if len(message) < 1:
        raise ValueError("请填写消息内容")
    contact_info = str(data.get("contact_info") or data.get("contact") or "").strip()
    contact_name = str(data.get("contact_name") or data.get("name") or "").strip()
    if user and user.get("kind") == "public":
        contact_name = contact_name or str(user.get("display_name") or user.get("account") or "")
        contact_info = contact_info or str(user.get("phone") or user.get("email") or user.get("account") or "")
    elif len(contact_info) < 3:
        raise ValueError("请填写联系方式，方便回复")
    guest_token = guest_token or secrets.token_urlsafe(24)
    user_id = int(user["id"]) if user and user.get("kind") == "public" else None
    fields = {
        "user_id": user_id,
        "guest_token": guest_token,
        "contact_name": contact_name[:80],
        "contact_info": contact_info[:160],
        "product_type": normalize_product_type(data.get("product_type")),
        "product_id": int(data.get("product_id") or 0) or None,
        "product_title": str(data.get("product_title") or data.get("vehicle_interest") or "在线询价").strip()[:180],
        "product_url": str(data.get("product_url") or "").strip()[:260],
        "product_image": str(data.get("product_image") or "").strip()[:260],
        "message": message[:2000],
        "sender_kind": "user" if user_id else "guest",
        "sender_name": (contact_name or str(user.get("account", "") if user else "") or "客户")[:80],
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_threads
            (user_id, guest_token, contact_name, contact_info, product_type, product_id,
             product_title, product_url, product_image, status, last_message, last_sender,
             last_message_at, admin_unread, user_unread)
            VALUES
            (:user_id, :guest_token, :contact_name, :contact_info, :product_type, :product_id,
             :product_title, :product_url, :product_image, 'open', :message, :sender_kind,
             CURRENT_TIMESTAMP, 1, 0)
            """,
            fields,
        )
        thread_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO chat_messages (thread_id, sender_kind, sender_name, body)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, fields["sender_kind"], fields["sender_name"], fields["message"]),
        )
    return get_chat_thread_payload(thread_id, include_token=True)

def append_chat_message(
    thread_id: int,
    data: dict[str, Any],
    sender_kind: str,
    sender_name: str = "",
) -> dict[str, Any]:
    if sender_kind not in {"guest", "user", "admin"}:
        raise ValueError("无效的消息发送方")
    body = str(data.get("message") or data.get("body") or "").strip()
    if len(body) < 1:
        raise ValueError("请填写消息内容")
    body = body[:2000]
    sender_name = sender_name[:80] or ("管理员" if sender_kind == "admin" else "客户")
    with connect() as conn:
        row = conn.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
        if not row:
            raise ValueError("消息会话不存在")
        conn.execute(
            """
            INSERT INTO chat_messages (thread_id, sender_kind, sender_name, body)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, sender_kind, sender_name, body),
        )
        admin_unread = 0 if sender_kind == "admin" else 1
        user_unread = 1 if sender_kind == "admin" else 0
        conn.execute(
            """
            UPDATE chat_threads
            SET last_message=?, last_sender=?, last_message_at=CURRENT_TIMESTAMP,
                admin_unread=?, user_unread=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (body, sender_kind, admin_unread, user_unread, thread_id),
        )
    return get_chat_thread_payload(thread_id, include_token=sender_kind != "admin")

def update_chat_thread_status(thread_id: int, data: dict[str, Any]) -> dict[str, Any]:
    status = str(data.get("status", "")).strip()
    if status not in CHAT_STATUSES:
        raise ValueError("无效的消息状态")
    with connect() as conn:
        conn.execute("UPDATE chat_threads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, thread_id))
    return get_chat_thread_payload(thread_id)
