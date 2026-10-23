"""Build a small, auditable archive of files required by the live site.

Usage:
    python scripts/build_release.py --check
    python scripts/build_release.py C:/path/to/tlhdd-release.tar.gz
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class AssetReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.urls.append(value)


def release_files() -> list[Path]:
    from app_config import PUBLIC_ROOT_FILES

    files = {path for path in ROOT.glob("*.py") if not path.name.startswith("test_")} | {ROOT / name for name in PUBLIC_ROOT_FILES}
    files |= {ROOT / "requirements.txt", ROOT / "schema.mysql.sql"}
    files |= {path for directory in ("assets", "admin") for path in (ROOT / directory).rglob("*") if path.is_file()}
    files.add(ROOT / "deploy/nginx/tlhdd.cn.conf")
    files.add(ROOT / "scripts/migrate_media.py")
    files.add(ROOT / "scripts/benchmark_public_api.py")
    files.add(ROOT / "admin-vben/LICENSE")
    return sorted(files)


def validate_release(files: list[Path]) -> None:
    from content_defaults import PAGE_MEDIA_DEFAULTS

    packaged = {path.relative_to(ROOT).as_posix() for path in files}
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError("Missing release files: " + ", ".join(missing))

    for path in files:
        if ROOT not in path.resolve().parents:
            raise RuntimeError(f"Release file escapes project directory: {path}")
        if path.suffix == ".map" or path.name.startswith(".env"):
            raise RuntimeError(f"Unexpected generated or secret file: {path}")

    for html in ROOT.glob("*.html"):
        parser = AssetReferences()
        parser.feed(html.read_text(encoding="utf-8"))
        for url in parser.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or url.startswith(("#", "mailto:", "tel:")):
                continue
            local = parsed.path.lstrip("/")
            if local and local not in packaged:
                raise RuntimeError(f"{html.name} references unpackaged file: {local}")
        if "images.unsplash.com" in html.read_text(encoding="utf-8"):
            raise RuntimeError(f"{html.name} still depends on a stock image host")

    for media in PAGE_MEDIA_DEFAULTS:
        url = media["default_url"]
        if not url.startswith("/assets/") or url.lstrip("/") not in packaged:
            raise RuntimeError(f"Media default is not bundled: {media['page_key']}/{media['media_key']} {url}")

    if "admin/index.html" not in packaged or "admin/lucide-local.js" not in packaged:
        raise RuntimeError("The published admin bundle is incomplete")
    admin_html = (ROOT / "admin/index.html").read_text(encoding="utf-8")
    for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script>", admin_html, re.DOTALL):
        if body.strip() and not re.search(r"\bsrc\s*=", attrs) and not re.search(r'type=["\']application/(?:ld\+)?json["\']', attrs):
            raise RuntimeError("Admin inline script conflicts with CSP; run python scripts/prepare_admin.py")
    if "loading-theme.js" in admin_html and "admin/loading-theme.js" not in packaged:
        raise RuntimeError("Admin loading-theme.js is not bundled")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without creating an archive")
    args = parser.parse_args()
    if not args.check and not args.archive:
        parser.error("archive path is required unless --check is used")

    files = release_files()
    validate_release(files)
    size = sum(path.stat().st_size for path in files)
    print(f"Release validated: {len(files)} files, {size / 1024 / 1024:.1f} MiB before compression")
    if args.check:
        return

    archive = args.archive.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "w:gz") as package:
        for path in files:
            package.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
    print(f"Created {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
