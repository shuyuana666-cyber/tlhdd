from __future__ import annotations

import json
import os
import hmac
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from database import connect, export_backup_sql
from cache_service import get_or_load, route_cache_key
from media_storage import StorageUnavailable, public_media_url, rewrite_public_media, settings as storage_settings
from app_config import RETIRED_PAGE_KEYS
from init_service import init_db
from admin_service import admin_dashboard_summary, bulk_delete_inventory, list_admin_parts, list_admin_vehicles
from mcp_service import MCP_TOOLS, mcp_call_tool, mcp_tool_error
from auth_service import (
    change_admin_password,
    change_public_password,
    create_public_user,
    delete_public_user,
    list_public_users,
    login_admin,
    login_public_user,
    public_user_payload,
    update_public_profile,
)
from catalog_service import (
    clamp_int,
    get_public_part,
    get_public_vehicle,
    global_search,
    list_catalog_terms,
    public_part_payload,
    public_vehicle_payload,
    save_catalog_term,
    save_part,
    save_vehicle,
    search_vehicles,
)
from chat_service import (
    append_chat_message,
    create_chat_thread,
    delete_chat_thread,
    ensure_chat_access,
    get_chat_thread_payload,
    guest_token_from_request,
    list_chat_threads,
    update_chat_thread_status,
)
from app_config import (
    ALLOWED_CORS_ORIGINS,
    DEFAULT_ADMIN_USER,
    MCP_PROTOCOL_VERSION,
    MCP_SUPPORTED_PROTOCOL_VERSIONS,
    TLHDD_MCP_TOKEN,
)
from content_service import (
    get_settings,
    list_page_media,
    list_page_sections,
    remove_page_media,
    save_hero_slide,
    save_metric,
    save_page_media,
    save_page_section,
    save_page_section_item,
    save_settings,
)
from exchange_rates import get_exchange_rate, get_exchange_rates, normalize_currency_targets
from inquiry_service import (
    create_inquiry,
    list_inquiries,
    list_user_inquiries,
    update_inquiry,
)
from forum_service import (
    create_forum_post,
    get_public_forum_post,
    list_forum_posts,
    list_user_forum_posts,
)
from static_files import static_access_status
from news_service import delete_news, get_news, list_news, save_news
from record_utils import row_to_dict, with_image_variants
from repositories import list_records
from http_utils import (
    PayloadTooLarge,
    allow_rate,
    auth_token,
    clear_cookie_header,
    cookie_header,
    parse_json_body,
    parse_mcp_json_body,
    rate_limit_key,
)
from uploads import UploadQuotaExceeded, save_admin_media_file, save_forum_media_file, save_uploaded_file

BASE_DIR = Path(__file__).resolve().parent

def get_session_user(handler: SimpleHTTPRequestHandler) -> dict[str, Any] | None:
    token = auth_token(handler, "X-Admin-Token", "X-Public-Token")
    if not token:
        return None
    with connect() as conn:
        admin_row = conn.execute(
            """
            SELECT u.id, u.username, u.role
            FROM admin_sessions s
            JOIN admin_users u ON u.id = s.user_id
            WHERE s.token=? AND s.expires_at > UTC_TIMESTAMP()
            """,
            (token,),
        ).fetchone()
        if admin_row:
            user = row_to_dict(admin_row)
            user["account"] = user["username"]
            user["display_name"] = user["username"]
            user["kind"] = "admin"
            user["permission"] = "admin"
            return user
        public_row = conn.execute(
            """
            SELECT u.id, u.account, u.display_name, u.email, u.phone, u.region,
                   u.company, u.avatar_url, u.role, u.created_at, u.last_login_at
            FROM public_sessions s
            JOIN public_users u ON u.id = s.user_id
            WHERE s.token=? AND s.expires_at > UTC_TIMESTAMP()
            """,
            (token,),
        ).fetchone()
    if public_row:
        return public_user_payload(public_row)
    return None

def get_public_session_user(handler: SimpleHTTPRequestHandler) -> dict[str, Any] | None:
    token = auth_token(handler, "X-Public-Token", cookie_names=("tlhdd_public_session",))
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.account, u.display_name, u.email, u.phone, u.region,
                   u.company, u.avatar_url, u.role, u.created_at, u.last_login_at
            FROM public_sessions s
            JOIN public_users u ON u.id = s.user_id
            WHERE s.token=? AND s.expires_at > UTC_TIMESTAMP()
            """,
            (token,),
        ).fetchone()
    return public_user_payload(row) if row else None

def require_admin(handler: SimpleHTTPRequestHandler) -> bool:
    user = get_session_user(handler)
    if user and user.get("permission") == "admin":
        return True
    send_json(handler, {"error": "Forbidden"}, HTTPStatus.FORBIDDEN if user else HTTPStatus.UNAUTHORIZED)
    return False

def same_origin_request(handler: SimpleHTTPRequestHandler) -> bool:
    host = handler.headers.get("Host", "").strip().lower()
    allowed = {f"http://{host}", f"https://{host}"} | ALLOWED_CORS_ORIGINS
    for header in ("Origin", "Referer"):
        raw = handler.headers.get(header, "").strip()
        if not raw:
            continue
        parsed = urlparse(raw)
        if f"{parsed.scheme}://{parsed.netloc}".lower() not in allowed:
            return False
    return True

def require_admin_write(handler: SimpleHTTPRequestHandler) -> bool:
    if not require_admin(handler):
        return False
    if not same_origin_request(handler):
        send_json(handler, {"error": "Forbidden"}, HTTPStatus.FORBIDDEN)
        return False
    return True

def public_session_response(session: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in session.items() if key != "token"}
    return payload

def send_json(handler: SimpleHTTPRequestHandler, payload: Any, status: HTTPStatus = HTTPStatus.OK, *, cache_status: str = "") -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    if cache_status:
        handler.send_header("X-Data-Cache", cache_status)
    handler.end_headers()
    handler.wfile.write(body)


def send_public_json(handler: SimpleHTTPRequestHandler, loader) -> None:
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query, keep_blank_values=True)
    payload, cache_status = get_or_load(route_cache_key(parsed.path, params), loader)
    send_json(handler, rewrite_public_media(payload), cache_status=cache_status)

def send_no_content(handler: SimpleHTTPRequestHandler, status: HTTPStatus = HTTPStatus.NO_CONTENT) -> None:
    handler.send_response(status)
    handler.send_header("Content-Length", "0")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()

def pagination_from_params(params: dict[str, list[str]], default_page_size: int = 20, max_page_size: int = 200) -> tuple[int, int]:
    page = clamp_int(params.get("page", ["1"])[0], 1, 1, 100000)
    page_size = clamp_int(params.get("page_size", [str(default_page_size)])[0], default_page_size, 1, max_page_size)
    return page, page_size

def mcp_authorized(handler: SimpleHTTPRequestHandler) -> bool:
    if not TLHDD_MCP_TOKEN:
        send_json(handler, {"error": "MCP is not configured"}, HTTPStatus.SERVICE_UNAVAILABLE)
        return False
    if not allow_rate(rate_limit_key(handler, "mcp_auth"), 120):
        send_json(handler, {"error": "MCP 请求过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
        return False
    auth = handler.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, TLHDD_MCP_TOKEN):
        send_json(handler, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
        return False
    return True

def mcp_http_protocol_supported(handler: SimpleHTTPRequestHandler) -> bool:
    version = handler.headers.get("MCP-Protocol-Version", "").strip()
    if version and version not in MCP_SUPPORTED_PROTOCOL_VERSIONS:
        send_json(handler, {"error": "Unsupported MCP-Protocol-Version"}, HTTPStatus.BAD_REQUEST)
        return False
    return True

def mcp_negotiated_protocol(params: dict[str, Any]) -> str:
    requested = str(params.get("protocolVersion") or "").strip()
    if requested in MCP_SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return MCP_PROTOCOL_VERSION

def mcp_result_for_request(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    try:
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            result = {
                "protocolVersion": mcp_negotiated_protocol(params),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "tlhdd-site-mcp",
                    "title": "通利华汽车集团上架接口",
                    "version": "1.0.0",
                },
                "instructions": "仅用于查询、上架和编辑车辆及配件；新增前请先搜索避免重复。",
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": MCP_TOOLS}
        elif method == "tools/call":
            tool_name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            result = mcp_call_tool(tool_name, arguments)
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except ValueError as exc:
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": request_id, "result": mcp_tool_error(str(exc))}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}
    except Exception as exc:
        print(f"MCP error: {exc}")
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": "MCP 工具执行失败"}}

def handle_mcp_request(handler: SimpleHTTPRequestHandler) -> None:
    if not mcp_authorized(handler):
        return
    if not mcp_http_protocol_supported(handler):
        return
    try:
        payload = parse_mcp_json_body(handler)
    except PayloadTooLarge as exc:
        send_json(handler, {"error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        return
    except ValueError as exc:
        send_json(handler, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return
    if isinstance(payload, list):
        responses = [response for item in payload if isinstance(item, dict) for response in [mcp_result_for_request(item)] if response is not None]
        if responses:
            send_json(handler, responses)
        else:
            send_no_content(handler, HTTPStatus.ACCEPTED)
        return
    if not isinstance(payload, dict):
        send_json(handler, {"error": "请求内容格式错误"}, HTTPStatus.BAD_REQUEST)
        return
    response = mcp_result_for_request(payload)
    if response is None:
        send_no_content(handler, HTTPStatus.ACCEPTED)
        return
    send_json(handler, response)

class TlhddHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Token, X-Public-Token, X-Guest-Token")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        media_base = urlparse(storage_settings()["base"])
        media_origin = f" {media_base.scheme}://{media_base.netloc}" if media_base.netloc else ""
        content_security_policy = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data: blob: https:; media-src 'self' blob:{media_origin}; font-src 'self' data:; connect-src 'self'; "
            "frame-src https://www.openstreetmap.org; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower()
        if forwarded_proto == "https":
            content_security_policy += "; upgrade-insecure-requests"
        self.send_header("Content-Security-Policy", content_security_policy)
        if urlparse(self.path).path.startswith("/admin"):
            self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive")
        if not self.path.startswith("/api/") and not getattr(self, "_media_redirect", False):
            request_path = urlparse(self.path).path
            suffix = Path(request_path).suffix.lower()
            if suffix in {".css", ".js"}:
                self.send_header("Cache-Control", "no-cache")
            elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".svg", ".mp4", ".webm", ".mov"}:
                self.send_header("Cache-Control", "public, max-age=604800")
            elif suffix in {".html", ""}:
                self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def send_head(self):
        parsed = urlparse(self.path)
        blocked_status = static_access_status(parsed.path)
        if blocked_status:
            self.send_error(blocked_status)
            return None
        media_url = public_media_url(parsed.path)
        if media_url != parsed.path:
            self._media_redirect = True
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", media_url)
            # Keep old paths reversible; the CDN object itself has a long TTL.
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        return super().send_head()

    def guess_type(self, path: str) -> str:
        if path.endswith(".webp"):
            return "image/webp"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        return super().guess_type(path)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/mcp":
            if not mcp_authorized(self) or not mcp_http_protocol_supported(self):
                return
            send_json(self, {"error": "Method not allowed"}, HTTPStatus.METHOD_NOT_ALLOWED)
            return
        if self._route_public_get(parsed):
            return
        if self._route_account_get(parsed):
            return
        if self._route_admin_get(parsed):
            return
        if parsed.path == "/admin":
            # Keep the trailing slash so the relative admin assets resolve under
            # /admin/ instead of incorrectly resolving to the site root.
            location = "/admin/"
            if parsed.query:
                location += "?" + parsed.query
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.end_headers()
            return
        super().do_GET()

    def _route_public_get(self, parsed) -> bool:
        return (
            self._route_public_search_site_get(parsed)
            or self._route_public_vehicle_get(parsed)
            or self._route_public_part_get(parsed)
            or self._route_exchange_rate_get(parsed)
            or self._route_site_page_get(parsed)
            or self._route_forum_read_get(parsed)
        )

    def _route_public_search_site_get(self, parsed) -> bool:
        if parsed.path == "/api/news":
            params = parse_qs(parsed.query)
            send_public_json(self, lambda: {"news": list_news(category=params.get("category", [""])[0])})
            return True
        if parsed.path.startswith("/api/news/"):
            try:
                send_public_json(self, lambda: {"article": get_news(parsed.path.removeprefix("/api/news/").strip("/"))})
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return True
            return True
        if parsed.path == "/api/search":
            if not allow_rate(rate_limit_key(self, "site_search"), 90):
                send_json(self, {"error": "搜索过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            query = parse_qs(parsed.query).get("q", [""])[0]
            send_public_json(self, lambda: global_search(query))
            return True
        if parsed.path == "/api/site":
            send_public_json(
                self,
                lambda: {
                    "hero_slides": [with_image_variants(item) for item in list_records("hero_slides", "WHERE is_active=1")],
                    "home_metrics": list_records("home_metrics", "WHERE is_active=1"),
                    "vehicles": [],
                    "parts": [],
                    "catalog_terms": list_catalog_terms(),
                    "forum_posts": [],
                    "settings": get_settings(),
                    "page_sections": list_page_sections(),
                    "page_media": list_page_media(),
                    "news": list_news(),
                },
            )
            return True
        return False

    def _route_public_vehicle_get(self, parsed) -> bool:
        if parsed.path == "/api/vehicles":
            send_public_json(self, lambda: public_vehicle_payload(parse_qs(parsed.query)))
            return True
        if parsed.path == "/api/vehicles/search":
            params = parse_qs(parsed.query)
            send_json(
                self,
                {
                    "vehicles": search_vehicles(
                        params.get("q", [""])[0],
                        params.get("type", [""])[0],
                    )
                },
            )
            return True
        if parsed.path.startswith("/api/vehicles/"):
            raw_id = parsed.path.removeprefix("/api/vehicles/").strip("/")
            try:
                send_public_json(self, lambda: {"vehicle": get_public_vehicle(int(raw_id), parse_qs(parsed.query).get("type", [""])[0])})
            except (TypeError, ValueError):
                send_json(self, {"error": "车辆不存在"}, HTTPStatus.NOT_FOUND)
                return True
            return True
        return False

    def _route_public_part_get(self, parsed) -> bool:
        if parsed.path == "/api/parts":
            send_public_json(self, lambda: public_part_payload(parse_qs(parsed.query)))
            return True
        if parsed.path.startswith("/api/parts/"):
            raw_id = parsed.path.removeprefix("/api/parts/").strip("/")
            try:
                send_public_json(self, lambda: {"part": get_public_part(int(raw_id))})
            except (TypeError, ValueError):
                send_json(self, {"error": "配件不存在"}, HTTPStatus.NOT_FOUND)
                return True
            return True
        return False

    def _route_exchange_rate_get(self, parsed) -> bool:
        if parsed.path == "/api/exchange-rate":
            params = parse_qs(parsed.query)
            try:
                base = params.get("base", ["CNY"])[0]
                if "targets" in params:
                    payload = get_exchange_rates(base, normalize_currency_targets(params.get("targets", ["RUB"])))
                    send_json(self, {"rates": payload})
                    return True
                rate = get_exchange_rate(base, params.get("target", ["RUB"])[0])
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
                return True
            send_json(self, {"rate": rate})
            return True
        return False

    def _route_site_page_get(self, parsed) -> bool:
        if parsed.path.startswith("/api/pages/"):
            page_key = parsed.path.removeprefix("/api/pages/").strip("/")
            if not page_key:
                send_json(self, {"error": "Invalid page"}, HTTPStatus.BAD_REQUEST)
                return True
            if page_key in RETIRED_PAGE_KEYS:
                send_json(self, {"error": "页面不存在"}, HTTPStatus.NOT_FOUND)
                return True
            send_public_json(self, lambda: {"sections": list_page_sections(page_key)})
            return True
        return False

    def _route_forum_read_get(self, parsed) -> bool:
        if parsed.path.startswith("/api/forum/posts/"):
            raw_id = parsed.path.removeprefix("/api/forum/posts/").strip("/")
            try:
                post_id = int(raw_id)
                post = get_public_forum_post(post_id)
            except (TypeError, ValueError):
                send_json(self, {"error": "帖子不存在"}, HTTPStatus.NOT_FOUND)
                return True
            send_public_json(self, lambda: {"post": post})
            return True
        if parsed.path == "/api/forum/posts":
            params = parse_qs(parsed.query)
            send_public_json(
                self,
                lambda: {
                    "posts": list_forum_posts(
                        params.get("q", [""])[0],
                        category=params.get("category", [""])[0],
                    )
                },
            )
            return True
        return False

    def _route_account_get(self, parsed) -> bool:
        if parsed.path == "/api/admin/me":
            user = get_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            send_json(self, {"user": user})
            return True
        if parsed.path == "/api/auth/me":
            user = get_public_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            send_json(self, {"user": user})
            return True
        if parsed.path == "/api/auth/inquiries":
            user = get_public_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            send_json(self, {"inquiries": list_user_inquiries(int(user["id"]))})
            return True
        if parsed.path == "/api/auth/forum-posts":
            user = get_public_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            send_json(self, {"posts": list_user_forum_posts(int(user["id"]))})
            return True
        if parsed.path == "/api/auth/messages":
            user = get_public_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            send_json(self, {"threads": list_chat_threads(user_id=int(user["id"]))})
            return True
        if parsed.path.startswith("/api/messages/threads/"):
            raw_id = parsed.path.removeprefix("/api/messages/threads/").strip("/")
            try:
                thread_id = int(raw_id)
                user = get_public_session_user(self)
                guest_token = guest_token_from_request(self)
                ensure_chat_access(thread_id, user=user, guest_token=guest_token)
                payload = get_chat_thread_payload(thread_id, include_token=not bool(user), mark_for="user")
            except PermissionError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.FORBIDDEN)
                return True
            except (TypeError, ValueError):
                send_json(self, {"error": "消息会话不存在"}, HTTPStatus.NOT_FOUND)
                return True
            send_json(self, payload)
            return True
        return False

    def _route_admin_get(self, parsed) -> bool:
        return (
            self._route_admin_snapshot_get(parsed)
            or self._route_admin_inventory_get(parsed)
            or self._route_admin_activity_get(parsed)
            or self._route_admin_backup_get(parsed)
        )

    def _route_admin_snapshot_get(self, parsed) -> bool:
        if parsed.path == "/api/admin/news":
            if not require_admin(self):
                return True
            params = parse_qs(parsed.query)
            send_json(self, {"news": list_news(admin=True, query=params.get("q", [""])[0], status=params.get("status", [""])[0])})
            return True
        if parsed.path == "/api/admin/all":
            if not require_admin(self):
                return True
            vehicle_page = list_admin_vehicles(page=1, page_size=12)
            part_page = list_admin_parts(page=1, page_size=50)
            send_json(
                self,
                {
                    "hero_slides": list_records("hero_slides"),
                    "home_metrics": list_records("home_metrics"),
                    "vehicles": vehicle_page["items"],
                    "vehicle_pagination": vehicle_page["pagination"],
                    "parts": part_page["items"],
                    "part_pagination": part_page["pagination"],
                    "catalog_terms": list_catalog_terms(admin=True),
                    "public_users": list_public_users(),
                    "inquiries": list_inquiries(),
                    "chat_threads": list_chat_threads(),
                    "settings": get_settings(),
                    "page_sections": list_page_sections(admin=True),
                    "page_media": list_page_media(),
                    "dashboard_summary": admin_dashboard_summary(),
                },
            )
            return True
        return False

    def _route_admin_inventory_get(self, parsed) -> bool:
        if parsed.path == "/api/admin/vehicles":
            if not require_admin(self):
                return True
            params = parse_qs(parsed.query)
            page, page_size = pagination_from_params(params, 12, 100)
            payload = list_admin_vehicles(
                params.get("q", [""])[0],
                params.get("type", [""])[0],
                params.get("status", [""])[0],
                page,
                page_size,
            )
            send_json(self, {"vehicles": payload["items"], "pagination": payload["pagination"]})
            return True
        if parsed.path == "/api/admin/parts":
            if not require_admin(self):
                return True
            params = parse_qs(parsed.query)
            page, page_size = pagination_from_params(params, 50, 100)
            payload = list_admin_parts(
                params.get("q", [""])[0],
                params.get("status", [""])[0],
                page,
                page_size,
            )
            send_json(self, {"parts": payload["items"], "pagination": payload["pagination"]})
            return True
        if parsed.path == "/api/admin/summary":
            if not require_admin(self):
                return True
            send_json(self, {"summary": admin_dashboard_summary()})
            return True
        return False

    def _route_admin_activity_get(self, parsed) -> bool:
        if parsed.path == "/api/admin/messages":
            if not require_admin(self):
                return True
            params = parse_qs(parsed.query)
            send_json(self, {"threads": list_chat_threads(params.get("q", [""])[0], params.get("status", [""])[0])})
            return True
        if parsed.path.startswith("/api/admin/messages/"):
            if not require_admin(self):
                return True
            raw_id = parsed.path.removeprefix("/api/admin/messages/").strip("/")
            try:
                thread_id = int(raw_id)
                payload = get_chat_thread_payload(thread_id, mark_for="admin")
            except (TypeError, ValueError):
                send_json(self, {"error": "消息会话不存在"}, HTTPStatus.NOT_FOUND)
                return True
            send_json(self, payload)
            return True
        if parsed.path == "/api/admin/inquiries":
            if not require_admin(self):
                return True
            params = parse_qs(parsed.query)
            send_json(self, {"inquiries": list_inquiries(params.get("q", [""])[0], params.get("status", [""])[0])})
            return True
        if parsed.path == "/api/admin/settings":
            if not require_admin(self):
                return True
            send_json(self, {"settings": get_settings()})
            return True
        return False

    def _route_admin_backup_get(self, parsed) -> bool:
        if parsed.path == "/api/admin/backup":
            if not require_admin(self):
                return True
            stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            try:
                data = export_backup_sql()
            except Exception as exc:
                print(f"Database backup error: {exc}")
                send_json(self, {"error": "数据库备份失败，请稍后重试"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return True
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/sql; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=tlhdd-mysql-{stamp}.sql")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return True
        return False

    def do_POST(self) -> None:
        self.route_write("POST")

    def do_PUT(self) -> None:
        self.route_write("PUT")

    def do_PATCH(self) -> None:
        self.route_write("PATCH")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/admin/") or not require_admin_write(self):
            return
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 4:
            send_json(self, {"error": "Invalid endpoint"}, HTTPStatus.NOT_FOUND)
            return
        _, _, resource, item_id = parts
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError):
            send_json(self, {"error": "无效的 ID"}, HTTPStatus.BAD_REQUEST)
            return
        if resource == "news":
            try:
                result = delete_news(item_id_int)
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            send_json(self, result)
            return
        if resource == "inquiries":
            with connect() as conn:
                cur = conn.execute("DELETE FROM inquiries WHERE id=?", (item_id_int,))
                if cur.rowcount <= 0:
                    send_json(self, {"error": "询盘不存在或已删除"}, HTTPStatus.NOT_FOUND)
                    return
            send_json(self, {"ok": True})
            return
        if resource == "messages":
            try:
                result = delete_chat_thread(item_id_int)
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            send_json(self, result)
            return
        if resource == "users":
            try:
                result = delete_public_user(item_id_int)
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            send_json(self, result)
            return
        if resource == "page-sections":
            with connect() as conn:
                conn.execute("DELETE FROM page_section_items WHERE section_id=?", (item_id_int,))
                cur = conn.execute("DELETE FROM page_sections WHERE id=?", (item_id_int,))
                if cur.rowcount <= 0:
                    send_json(self, {"error": "页面区块不存在或已删除"}, HTTPStatus.NOT_FOUND)
                    return
            send_json(self, {"ok": True})
            return
        if resource == "page-section-items":
            with connect() as conn:
                cur = conn.execute("DELETE FROM page_section_items WHERE id=?", (item_id_int,))
                if cur.rowcount <= 0:
                    send_json(self, {"error": "页面内容项不存在或已删除"}, HTTPStatus.NOT_FOUND)
                    return
            send_json(self, {"ok": True})
            return
        if resource == "page-media":
            try:
                result = remove_page_media(item_id_int)
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            send_json(self, result)
            return
        if resource == "catalog-terms":
            with connect() as conn:
                cur = conn.execute("DELETE FROM catalog_terms WHERE id=?", (item_id_int,))
                if cur.rowcount <= 0:
                    send_json(self, {"error": "删除失败，记录不存在或已被删除"}, HTTPStatus.NOT_FOUND)
                    return
            send_json(self, {"ok": True})
            return
        table = {"slides": "hero_slides", "metrics": "home_metrics", "vehicles": "vehicles", "parts": "parts"}.get(resource)
        if not table:
            send_json(self, {"error": "Unknown resource"}, HTTPStatus.NOT_FOUND)
            return
        with connect() as conn:
            cur = conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id_int,))
            if cur.rowcount <= 0:
                send_json(self, {"error": "删除失败，记录不存在或已被删除"}, HTTPStatus.NOT_FOUND)
                return
        send_json(self, {"ok": True})

    def route_write(self, method: str) -> None:
        try:
            self._route_write_impl(method)
        except PayloadTooLarge as exc:
            send_json(self, {"error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except ValueError as exc:
            send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _route_write_impl(self, method: str) -> None:
        path = urlparse(self.path).path
        if path == "/mcp":
            if method != "POST":
                send_json(self, {"error": "Method not allowed"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return
            handle_mcp_request(self)
            return
        if self._route_auth_write(path):
            return
        if self._route_visitor_write(path):
            return
        if self._route_password_change(path):
            return
        self._route_admin_write(path, method)

    def _send_session_response(
        self,
        session: dict[str, Any],
        status: HTTPStatus,
        cookie_name: str,
        max_age: int,
    ) -> None:
        self.send_response(status)
        body = json.dumps(public_session_response(session), ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", cookie_header(self, cookie_name, session["token"], max_age))
        self.end_headers()
        self.wfile.write(body)

    def _send_logout_response(self) -> None:
        self.send_response(HTTPStatus.OK)
        body = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", clear_cookie_header("tlhdd_admin_session"))
        self.send_header("Set-Cookie", clear_cookie_header("tlhdd_public_session"))
        self.end_headers()
        self.wfile.write(body)

    def _route_auth_write(self, path: str) -> bool:
        return self._route_admin_auth_write(path) or self._route_public_auth_write(path)

    def _route_admin_auth_write(self, path: str) -> bool:
        if path == "/api/admin/login":
            if not allow_rate(rate_limit_key(self, "admin_login"), 8):
                send_json(self, {"error": "尝试过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            data = parse_json_body(self)
            session = login_admin(data.get("username", "") or data.get("account", ""), data.get("password", ""))
            if not session:
                send_json(self, {"error": "账号或密码错误"}, HTTPStatus.UNAUTHORIZED)
                return True
            self._send_session_response(session, HTTPStatus.OK, "tlhdd_admin_session", 8 * 60 * 60)
            return True
        if path == "/api/admin/logout":
            token = auth_token(self, "X-Admin-Token", "X-Public-Token")
            if token:
                with connect() as conn:
                    conn.execute("DELETE FROM admin_sessions WHERE token=?", (token,))
                    conn.execute("DELETE FROM public_sessions WHERE token=?", (token,))
            self._send_logout_response()
            return True
        return False

    def _route_public_auth_write(self, path: str) -> bool:
        if path == "/api/auth/register":
            if not allow_rate(rate_limit_key(self, "public_register"), 6):
                send_json(self, {"error": "注册过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            data = parse_json_body(self)
            try:
                session = create_public_user(
                    data.get("account", ""),
                    data.get("password", ""),
                    data.get("display_name", ""),
                )
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            self._send_session_response(session, HTTPStatus.CREATED, "tlhdd_public_session", 30 * 24 * 60 * 60)
            return True
        if path == "/api/auth/login":
            if not allow_rate(rate_limit_key(self, "public_login"), 12):
                send_json(self, {"error": "尝试过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            data = parse_json_body(self)
            try:
                session = login_public_user(data.get("account", ""), data.get("password", ""))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                return True
            self._send_session_response(session, HTTPStatus.OK, "tlhdd_public_session", 30 * 24 * 60 * 60)
            return True
        if path == "/api/auth/profile":
            user = get_public_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            try:
                profile = update_public_profile(int(user["id"]), parse_json_body(self))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, {"user": profile})
            return True
        if path == "/api/auth/logout":
            token = auth_token(self, "X-Public-Token")
            if token:
                with connect() as conn:
                    conn.execute("DELETE FROM public_sessions WHERE token=?", (token,))
                    conn.execute("DELETE FROM admin_sessions WHERE token=?", (token,))
            self._send_logout_response()
            return True
        return False

    def _route_visitor_write(self, path: str) -> bool:
        return self._route_inquiry_chat_write(path) or self._route_forum_write(path)

    def _route_inquiry_chat_write(self, path: str) -> bool:
        if path == "/api/inquiries":
            if not allow_rate(rate_limit_key(self, "inquiry_submit"), 10):
                send_json(self, {"error": "提交过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            try:
                body_data = parse_json_body(self)
                inquiry = create_inquiry(body_data, get_public_session_user(self))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, {"inquiry": inquiry}, HTTPStatus.CREATED)
            return True
        if path == "/api/messages/threads":
            if not allow_rate(rate_limit_key(self, "message_thread"), 12):
                send_json(self, {"error": "消息提交过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            data = parse_json_body(self)
            try:
                payload = create_chat_thread(data, get_public_session_user(self), guest_token_from_request(self))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, payload, HTTPStatus.CREATED)
            return True
        if path.startswith("/api/messages/threads/"):
            if not allow_rate(rate_limit_key(self, "message_reply"), 30):
                send_json(self, {"error": "消息提交过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            data = parse_json_body(self)
            parts = path.strip("/").split("/")
            if len(parts) != 5 or parts[4] != "messages":
                send_json(self, {"error": "Invalid endpoint"}, HTTPStatus.NOT_FOUND)
                return True
            try:
                thread_id = int(parts[3])
                user = get_public_session_user(self)
                guest_token = guest_token_from_request(self)
                ensure_chat_access(thread_id, user=user, guest_token=guest_token)
                sender_kind = "user" if user else "guest"
                sender_name = str((user or {}).get("display_name") or (user or {}).get("account") or data.get("contact_name") or "客户")
                payload = append_chat_message(thread_id, data, sender_kind, sender_name)
            except PermissionError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.FORBIDDEN)
                return True
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, payload, HTTPStatus.CREATED)
            return True
        return False

    def _route_forum_write(self, path: str) -> bool:
        if path == "/api/forum/uploads":
            if not allow_rate(rate_limit_key(self, "forum_upload"), 12):
                send_json(self, {"error": "上传过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            user = get_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            try:
                result = save_forum_media_file(self, user)
            except StorageUnavailable as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return True
            except UploadQuotaExceeded as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, result, HTTPStatus.CREATED)
            return True
        if path == "/api/forum/posts":
            if not allow_rate(rate_limit_key(self, "forum_post"), 10):
                send_json(self, {"error": "发帖过于频繁，请稍后再试"}, HTTPStatus.TOO_MANY_REQUESTS)
                return True
            user = get_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            try:
                post = create_forum_post(user, parse_json_body(self))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, {"post": post}, HTTPStatus.CREATED)
            return True
        return False

    def _route_password_change(self, path: str) -> bool:
        if path == "/api/admin/change-password":
            user = get_session_user(self)
            if not user:
                send_json(self, {"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return True
            data = parse_json_body(self)
            try:
                if user.get("permission") == "admin":
                    ok = change_admin_password(int(user["id"]), data.get("old_password", ""), data.get("new_password", ""))
                else:
                    ok = change_public_password(int(user["id"]), data.get("old_password", ""), data.get("new_password", ""))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            if not ok:
                send_json(self, {"error": "旧密码不正确"}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, {"ok": True})
            return True
        return False

    def _route_admin_write(self, path: str, method: str) -> bool:
        if not path.startswith("/api/admin/") or not require_admin_write(self):
            return True
        if path in {"/api/admin/vehicles/bulk-delete", "/api/admin/parts/bulk-delete"}:
            if method != "POST":
                send_json(self, {"error": "Method not allowed"}, HTTPStatus.METHOD_NOT_ALLOWED)
                return True
            data = parse_json_body(self)
            try:
                result = bulk_delete_inventory(path.split("/")[3], data.get("ids"))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            except Exception as exc:
                print(f"Bulk delete error: {exc}")
                send_json(self, {"error": "批量删除失败，请稍后重试"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return True
            send_json(self, result)
            return True
        if path == "/api/admin/upload":
            try:
                result = save_uploaded_file(self)
            except StorageUnavailable as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return True
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, result, HTTPStatus.CREATED)
            return True
        if path == "/api/admin/upload-media":
            try:
                result = save_admin_media_file(self)
            except StorageUnavailable as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return True
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, result, HTTPStatus.CREATED)
            return True
        if path.startswith("/api/admin/messages/") and path.endswith("/messages"):
            data = parse_json_body(self)
            parts = path.strip("/").split("/")
            if len(parts) != 5:
                send_json(self, {"error": "Invalid endpoint"}, HTTPStatus.NOT_FOUND)
                return True
            try:
                thread_id = int(parts[3])
                user = get_session_user(self) or {}
                payload = append_chat_message(thread_id, data, "admin", str(user.get("display_name") or user.get("username") or "管理员"))
            except ValueError as exc:
                send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return True
            send_json(self, payload, HTTPStatus.CREATED)
            return True
        data = parse_json_body(self)
        parts = path.strip("/").split("/")
        resource = parts[2] if len(parts) >= 3 else ""
        if resource == "news" and (len(parts) not in {3, 4} or (len(parts) == 4 and (not parts[3].isdigit() or int(parts[3]) < 1))):
            send_json(self, {"error": "新闻地址无效"}, HTTPStatus.BAD_REQUEST)
            return True
        item_id = int(parts[3]) if len(parts) == 4 else None
        try:
            if resource == "settings":
                result = {"settings": save_settings(data)}
            elif resource == "inquiries" and item_id:
                result = update_inquiry(item_id, data)
            elif resource == "slides":
                result = save_hero_slide(data, item_id)
            elif resource == "metrics":
                result = save_metric(data, item_id)
            elif resource == "vehicles":
                result = save_vehicle(data, item_id)
            elif resource == "parts":
                result = save_part(data, item_id)
            elif resource == "news":
                result = save_news(data, item_id)
            elif resource == "catalog-terms":
                result = save_catalog_term(data, item_id)
            elif resource == "messages" and item_id:
                result = update_chat_thread_status(item_id, data)
            elif resource == "page-sections":
                result = save_page_section(data, item_id)
            elif resource == "page-section-items":
                result = save_page_section_item(data, item_id)
            elif resource == "page-media" and item_id:
                result = save_page_media(data, item_id)
            else:
                send_json(self, {"error": "Unknown resource"}, HTTPStatus.NOT_FOUND)
                return True
        except ValueError as exc:
            send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return True
        except Exception as exc:
            print(f"API error: {exc}")
            send_json(self, {"error": "服务器处理失败，请稍后重试"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return True
        send_json(self, result, HTTPStatus.CREATED if method == "POST" else HTTPStatus.OK)
        return True

def main() -> None:
    storage_settings()  # Validate configuration before opening the HTTP listener.
    init_db()
    host = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("PORT", "4173"))
    server = ThreadingHTTPServer((host, port), TlhddHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"Tonglihua Automotive Group site running: http://{display_host}:{port}/")
    if host == "0.0.0.0":
        print(f"LAN access enabled: http://<local-ip>:{port}/")
    print(f"Admin panel: http://{display_host}:{port}/admin/  user={DEFAULT_ADMIN_USER}")
    server.serve_forever()

if __name__ == "__main__":
    main()
