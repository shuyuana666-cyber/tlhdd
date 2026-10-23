"""Externalize Vben's loading-theme script for the site's script-src 'self' CSP."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def prepare(directory: Path) -> None:
    index = directory / "index.html"
    html = index.read_text(encoding="utf-8")
    pattern = re.compile(r'<script\b(?P<attrs>[^>]*\bdata-app-loading=["\']inject-js["\'][^>]*)>(?P<code>.*?)</script>', re.DOTALL)
    matches = list(pattern.finditer(html))
    if not matches:
        raise RuntimeError("Vben loading script was not found; inspect the build before publishing")
    if len(matches) != 1:
        raise RuntimeError("Expected one loading-theme script")
    match = matches[0]
    if re.search(r'\bsrc\s*=', match["attrs"]):
        if not (directory / "loading-theme.js").is_file():
            raise RuntimeError("External loading-theme.js is missing")
        print("Admin loading-theme script is already external")
        return
    (directory / "loading-theme.js").write_text(match["code"].strip() + "\n", encoding="utf-8")
    tag = '<script' + match["attrs"] + ' src="./loading-theme.js"></script>'
    index.write_text(html[:match.start()] + tag + html[match.end():], encoding="utf-8")
    print("Admin loading-theme script externalized")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent / "admin")
    prepare(parser.parse_args().directory.resolve())


if __name__ == "__main__":
    main()
