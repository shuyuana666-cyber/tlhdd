from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DERIVATIVE_SUFFIXES = ("-optimized.webp", "-thumb.webp")

def is_source_image(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() in IMAGE_EXTS and not any(name.endswith(suffix) for suffix in DERIVATIVE_SUFFIXES)

def save_derivative(source: Path, suffix: str, max_size: tuple[int, int], quality: int, dry_run: bool) -> bool:
    target = source.with_name(f"{source.stem}-{suffix}.webp")
    if target.exists():
        return False
    if dry_run:
        print(f"[dry-run] {source} -> {target}")
        return True
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        image.thumbnail(max_size)
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        image.save(target, "WEBP", quality=quality, method=6)
    print(f"[ok] {source} -> {target}")
    return True

def optimize_uploads(root: Path, dry_run: bool = False) -> tuple[int, int, int]:
    scanned = 0
    created = 0
    failed = 0
    for source in root.rglob("*"):
        if not source.is_file() or not is_source_image(source):
            continue
        scanned += 1
        try:
            created += int(save_derivative(source, "optimized", (1400, 1400), 82, dry_run))
            created += int(save_derivative(source, "thumb", (640, 480), 76, dry_run))
        except Exception as exc:
            failed += 1
            print(f"[failed] {source}: {exc}")
    return scanned, created, failed

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate WebP optimized/thumb derivatives for upload images.")
    parser.add_argument("root", nargs="?", default="uploads", help="Uploads directory to scan.")
    parser.add_argument("--dry-run", action="store_true", help="Print work without writing files.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Uploads directory not found: {root}")
    scanned, created, failed = optimize_uploads(root, args.dry_run)
    print(f"scanned={scanned} created={created} failed={failed}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
