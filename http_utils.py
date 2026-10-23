from __future__ import annotations

import json
from datetime import datetime
from ipaddress import ip_address
from threading import Lock
from typing import Any

from app_config import FORCE_SECURE_COOKIES, TRUSTED_PROXY_IPS

MAX_JSON_BODY_BYTES = 256 * 1024
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}
RATE_LIMIT_LOCK = Lock()

class PayloadTooLarge(Exception):
    pass

def parse_json_body(handler: Any) -> dict[str, Any]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        raise ValueError("请求体长度无效")
    if length < 0:
        raise ValueError("请求体长度无效")
    if length > MAX_JSON_BODY_BYTES:
        raise PayloadTooLarge("请求内容过大，请精简后再提交")
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("请求内容不是有效的 JSON")
    if not isinstance(data, dict):
        raise ValueError("请求内容格式错误")
    return data

def parse_mcp_json_body(handler: Any) -> Any:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        raise ValueError("请求体长度无效")
    if length < 0:
        raise ValueError("请求体长度无效")
    if length > MAX_JSON_BODY_BYTES:
        raise PayloadTooLarge("请求内容过大，请精简后再提交")
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("请求内容不是有效的 JSON")

def client_ip(handler: Any) -> str:
    direct_ip = str(handler.client_address[0] if handler.client_address else "unknown")
    try:
        direct_ip = str(ip_address(direct_ip))
    except ValueError:
        return "unknown"
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if not forwarded or not is_trusted_proxy(direct_ip):
        return direct_ip
    hops: list[str] = []
    for item in forwarded.split(",")[-16:]:
        try:
            hops.append(str(ip_address(item.strip())))
        except ValueError:
            continue
    client = direct_ip
    for hop in reversed(hops):
        if not is_trusted_proxy(client):
            break
        client = hop
    return client

def is_trusted_proxy(value: str) -> bool:
    if value in TRUSTED_PROXY_IPS:
        return True
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return str(parsed) in TRUSTED_PROXY_IPS or parsed.is_loopback

def rate_limit_key(handler: Any, scope: str) -> str:
    return f"{scope}:{client_ip(handler)}"

def allow_rate(key: str, limit: int, window: int = RATE_LIMIT_WINDOW_SECONDS) -> bool:
    now = datetime.utcnow().timestamp()
    with RATE_LIMIT_LOCK:
        bucket = [stamp for stamp in RATE_LIMIT_BUCKETS.get(key, []) if now - stamp < window]
        if len(bucket) >= limit:
            RATE_LIMIT_BUCKETS[key] = bucket
            return False
        bucket.append(now)
        RATE_LIMIT_BUCKETS[key] = bucket
        if len(RATE_LIMIT_BUCKETS) > 2048:
            stale_before = now - window * 4
            for old_key in list(RATE_LIMIT_BUCKETS.keys()):
                RATE_LIMIT_BUCKETS[old_key] = [stamp for stamp in RATE_LIMIT_BUCKETS[old_key] if stamp > stale_before]
                if not RATE_LIMIT_BUCKETS[old_key]:
                    RATE_LIMIT_BUCKETS.pop(old_key, None)
        return True

def request_cookies(handler: Any) -> dict[str, str]:
    cookies: dict[str, str] = {}
    raw = handler.headers.get("Cookie", "")
    for chunk in raw.split(";"):
        if "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies

def cookie_token(handler: Any, names: tuple[str, ...]) -> str:
    cookies = request_cookies(handler)
    for name in names:
        token = cookies.get(name, "")
        if token:
            return token
    return ""

def cookie_header(handler: Any, name: str, value: str, max_age: int) -> str:
    attrs = [f"{name}={value}", "Path=/", f"Max-Age={max_age}", "HttpOnly", "SameSite=Lax"]
    if handler.headers.get("X-Forwarded-Proto", "").lower() == "https" or (FORCE_SECURE_COOKIES and not is_loopback_host(handler.headers.get("Host", ""))):
        attrs.append("Secure")
    return "; ".join(attrs)

def is_loopback_host(host_header: str) -> bool:
    host = host_header.strip().split(":", 1)[0].strip("[]").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False

def clear_cookie_header(name: str) -> str:
    return f"{name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"

def auth_token(
    handler: Any,
    *fallback_headers: str,
    cookie_names: tuple[str, ...] = ("tlhdd_admin_session", "tlhdd_public_session"),
) -> str:
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        if token:
            return token
    for header in fallback_headers:
        token = handler.headers.get(header, "").strip()
        if token:
            return token
    token = cookie_token(handler, cookie_names)
    if token:
        return token
    return ""
