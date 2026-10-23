"""Password hashing, authentication, registration, and public account data."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from database import DbRow, IntegrityError, connect
from record_utils import row_to_dict

MIN_PASSWORD_LENGTH = 12
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
LEGACY_PASSWORD_HASH_ITERATIONS = 120_000

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ITERATIONS
    )
    return salt, f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${digest.hex()}"

def _password_hash_parameters(password_hash: str) -> tuple[int, str] | None:
    if password_hash.startswith(f"{PASSWORD_HASH_ALGORITHM}$"):
        try:
            algorithm, raw_iterations, digest = password_hash.split("$", 2)
            iterations = int(raw_iterations)
        except (ValueError, TypeError):
            return None
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return None
        if iterations not in {PASSWORD_HASH_ITERATIONS, LEGACY_PASSWORD_HASH_ITERATIONS}:
            return None
        return iterations, digest
    return LEGACY_PASSWORD_HASH_ITERATIONS, password_hash

def _verify_password_details(password: str, salt: str, password_hash: str) -> tuple[bool, int | None]:
    parameters = _password_hash_parameters(password_hash)
    if not parameters:
        return False, None
    iterations, expected_digest = parameters
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()
    return secrets.compare_digest(digest, expected_digest), iterations

def verify_password(password: str, salt: str, password_hash: str) -> bool:
    valid, _ = _verify_password_details(password, salt, password_hash)
    return valid

def verify_password_with_upgrade(
    password: str, salt: str, password_hash: str
) -> tuple[bool, tuple[str, str] | None]:
    valid, iterations = _verify_password_details(password, salt, password_hash)
    if not valid:
        return False, None
    if iterations is not None and iterations < PASSWORD_HASH_ITERATIONS:
        return True, hash_password(password)
    return True, None

def public_user_payload(row: DbRow) -> dict[str, Any]:
    user = row_to_dict(row)
    user["username"] = user.get("account", "")
    user["kind"] = "public"
    user["permission"] = "user"
    return user

def login_admin(username: str, password: str) -> dict[str, Any] | None:
    username = username.strip()
    with connect() as conn:
        user = conn.execute("SELECT * FROM admin_users WHERE username=?", (username,)).fetchone()
        if not user:
            return None
        valid_password, upgraded_hash = verify_password_with_upgrade(
            password, user["password_salt"], user["password_hash"]
        )
        if not valid_password:
            return None
        if upgraded_hash:
            conn.execute(
                """UPDATE admin_users
                   SET password_salt=?, password_hash=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (*upgraded_hash, user["id"]),
            )
        token = secrets.token_urlsafe(32)
        conn.execute(
            """
            INSERT INTO admin_sessions (token, user_id, expires_at)
            VALUES (?, ?, DATE_ADD(UTC_TIMESTAMP(), INTERVAL 8 HOUR))
            """,
            (token, user["id"]),
        )
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "account": user["username"],
                "display_name": user["username"],
                "role": user["role"],
                "kind": "admin",
                "permission": "admin",
            },
        }

def change_admin_password(user_id: int, old_password: str, new_password: str) -> bool:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"新密码至少 {MIN_PASSWORD_LENGTH} 位")
    with connect() as conn:
        user = conn.execute("SELECT * FROM admin_users WHERE id=?", (user_id,)).fetchone()
        if not user or not verify_password(old_password, user["password_salt"], user["password_hash"]):
            return False
        salt, digest = hash_password(new_password)
        conn.execute(
            """
            UPDATE admin_users SET password_salt=?, password_hash=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (salt, digest, user_id),
        )
        conn.execute("DELETE FROM admin_sessions WHERE user_id=?", (user_id,))
        return True

def list_public_users() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, account, display_name, email, phone, region, company, avatar_url,
                   role, created_at, last_login_at
            FROM public_users
            ORDER BY id DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]

def delete_public_user(user_id: int) -> dict[str, Any]:
    """Hard-delete a public account and the business records it owns."""
    with connect() as conn:
        user = conn.execute("SELECT id FROM public_users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise ValueError("用户不存在或已删除")

        # These tables intentionally do not all have foreign keys. Remove
        # account-owned data explicitly so deletion does not leave orphaned
        # profile-linked inquiries, chat history, posts, or upload quotas.
        conn.execute("DELETE FROM inquiries WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM chat_threads WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM forum_posts WHERE user_kind='public' AND user_id=?",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM forum_upload_usage WHERE user_kind='public' AND user_id=?",
            (user_id,),
        )
        conn.execute("DELETE FROM public_sessions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM public_users WHERE id=?", (user_id,))
    return {"ok": True}

def create_public_user(account: str, password: str, display_name: str = "") -> dict[str, Any]:
    account = account.strip().lower()
    display_name = display_name.strip() or account.split("@")[0]
    if len(account) < 3:
        raise ValueError("账号至少 3 位")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"密码至少 {MIN_PASSWORD_LENGTH} 位")
    salt, digest = hash_password(password)
    try:
        with connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO public_users (account, display_name, password_salt, password_hash, role)
                VALUES (?, ?, ?, ?, '普通用户')
                """,
                (account, display_name, salt, digest),
            )
            user_id = int(cur.lastrowid)
    except IntegrityError as exc:
        raise ValueError("该账号已注册") from exc
    return login_public_user(account, password) | {"created": True, "user_id": user_id}

def login_public_user(account: str, password: str) -> dict[str, Any]:
    account = account.strip().lower()
    with connect() as conn:
        user = conn.execute("SELECT * FROM public_users WHERE account=?", (account,)).fetchone()
        if not user:
            raise ValueError("账号或密码错误")
        valid_password, upgraded_hash = verify_password_with_upgrade(
            password, user["password_salt"], user["password_hash"]
        )
        if not valid_password:
            raise ValueError("账号或密码错误")
        token = secrets.token_urlsafe(32)
        conn.execute(
            """
            INSERT INTO public_sessions (token, user_id, expires_at)
            VALUES (?, ?, DATE_ADD(UTC_TIMESTAMP(), INTERVAL 30 DAY))
            """,
            (token, user["id"]),
        )
        if upgraded_hash:
            conn.execute(
                """UPDATE public_users
                   SET password_salt=?, password_hash=?, last_login_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (*upgraded_hash, user["id"]),
            )
        else:
            conn.execute("UPDATE public_users SET last_login_at=CURRENT_TIMESTAMP WHERE id=?", (user["id"],))
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "account": user["account"],
                "username": user["account"],
                "display_name": user["display_name"],
                "email": user["email"],
                "phone": user["phone"],
                "region": user["region"],
                "company": user["company"],
                "avatar_url": user["avatar_url"],
                "role": user["role"],
                "kind": "public",
                "permission": "user",
            },
        }

def change_public_password(user_id: int, old_password: str, new_password: str) -> bool:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"新密码至少 {MIN_PASSWORD_LENGTH} 位")
    with connect() as conn:
        user = conn.execute("SELECT * FROM public_users WHERE id=?", (user_id,)).fetchone()
        if not user or not verify_password(old_password, user["password_salt"], user["password_hash"]):
            return False
        salt, digest = hash_password(new_password)
        conn.execute(
            """
            UPDATE public_users SET password_salt=?, password_hash=?
            WHERE id=?
            """,
            (salt, digest, user_id),
        )
        conn.execute("DELETE FROM public_sessions WHERE user_id=?", (user_id,))
        return True

def get_public_user(user_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, account, display_name, email, phone, region, company, avatar_url,
                   role, created_at, last_login_at
            FROM public_users
            WHERE id=?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        raise ValueError("用户不存在")
    return public_user_payload(row)

def update_public_profile(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "display_name": str(data.get("display_name", "")).strip()[:80],
        "email": str(data.get("email", "")).strip()[:120],
        "phone": str(data.get("phone", "")).strip()[:80],
        "region": str(data.get("region", "")).strip()[:120],
        "company": str(data.get("company", "")).strip()[:120],
        "avatar_url": str(data.get("avatar_url", "")).strip()[:500],
        "id": user_id,
    }
    if not fields["display_name"]:
        fields["display_name"] = get_public_user(user_id).get("account", "")
    with connect() as conn:
        conn.execute(
            """
            UPDATE public_users
            SET display_name=:display_name, email=:email, phone=:phone,
                region=:region, company=:company, avatar_url=:avatar_url
            WHERE id=:id
            """,
            fields,
        )
    return get_public_user(user_id)
