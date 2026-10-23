"""Preview media publishing; --apply uploads without changing database URLs or deleting files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from media_storage import StorageUnavailable, media_path, publish_file, settings


def candidates(*, include_assets: bool = False):
    directories = [ROOT / "uploads"]
    if include_assets:
        directories.extend([ROOT / "assets/default-media", ROOT / "assets/images"])
    for directory in directories:
        for path in sorted(directory.rglob("*")):
            if (path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
                    and media_path("/" + path.relative_to(ROOT).as_posix())):
                yield path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Publish and verify; default is preview only")
    parser.add_argument("--include-assets", action="store_true", help="Include public default-media and images")
    parser.add_argument("--verify-download", action="store_true", help="Read objects back and compare SHA-256 (extra traffic)")
    args = parser.parse_args()
    if args.apply:
        config = settings()
        if not config["bucket"]:
            parser.error("Set TLHDD_S3_BUCKET and credentials before --apply")
    count = uploaded = failed = size = 0
    for path in candidates(include_assets=args.include_assets):
        count += 1
        size += path.stat().st_size
        if args.apply:
            try:
                uploaded += int(publish_file(path, verify_download=args.verify_download))
            except StorageUnavailable:
                failed += 1
                print(f"Failed: {path.relative_to(ROOT).as_posix()}", file=sys.stderr)
    print(json.dumps({"mode": "apply" if args.apply else "preview", "files": count,
                      "bytes": size, "uploaded": uploaded, "failed": failed,
                      "unchanged": count - uploaded - failed if args.apply else 0}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
