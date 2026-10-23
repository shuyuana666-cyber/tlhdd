"""Application environment settings and static request allowlists."""

import os

ALLOWED_CORS_ORIGINS = {
    origin.strip()
    for origin in os.environ.get(
        "TLHDD_ALLOWED_ORIGINS",
        "http://127.0.0.1:4173,http://localhost:4173",
    ).split(",")
    if origin.strip()
}
DEFAULT_ADMIN_USER = os.environ.get("TLHDD_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("TLHDD_ADMIN_PASSWORD", "")
ENABLE_DEMO_SEED = os.environ.get("TLHDD_ENABLE_DEMO_SEED", "0").strip().lower() in {"1", "true", "yes", "on"}
TLHDD_MCP_TOKEN = os.environ.get("TLHDD_MCP_TOKEN", "").strip()
MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = {"2025-03-26", "2025-06-18", "2025-11-25"}
PUBLIC_STATIC_DIRS = {"assets", "uploads", "admin"}
PUBLIC_ROOT_FILES = {
    "index.html",
    "about.html",
    "new-cars.html",
    "used-cars.html",
    "contact.html",
    "user-center.html",
    "new-car-detail.html",
    "used-car-detail.html",
    "part-detail.html",
    "car-options.html",
    "transportation.html",
    "purchase-plan.html",
    "service-center.html",
    "news.html",
    "news-detail.html",
    "favicon.ico",
    "favicon.png",
    "apple-touch-icon.png",
    "6ef28aa143fc6f2c0549afdc7e3f26c1.txt",
}
BLOCKED_STATIC_DIRS = {
    ".git",
    ".playwright-cli",
    "__pycache__",
    "data",
    "logs",
    "node_modules",
    "output",
    "screenshots",
}
BLOCKED_STATIC_EXTS = {
    ".db", ".db-wal", ".db-shm", ".db-journal",
    ".py", ".pyc", ".log", ".gz", ".zip", ".7z", ".tar", ".pma",
}
DEFAULT_TRUSTED_PROXY_IPS = {"127.0.0.1", "::1"}
TRUSTED_PROXY_IPS = DEFAULT_TRUSTED_PROXY_IPS | {
    ip.strip() for ip in os.environ.get("TRUSTED_PROXY_IPS", "").split(",") if ip.strip()
}
FORCE_SECURE_COOKIES = os.environ.get("FORCE_SECURE_COOKIES", "1").strip().lower() not in {"0", "false", "no"}
RETIRED_PAGE_KEYS = ("customization", "logistics", "purchase")
