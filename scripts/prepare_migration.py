"""Prepare a checked MySQL export and complete uploads archive for deployment.

Run from the project root with an empty, private output directory:
    python scripts/prepare_migration.py C:/private/tlhdd-deploy

The output contains customer data. Transfer it over SSH and remove it after
the remote import and backup checks have succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
UPLOAD_ROOT = ROOT / "uploads"
UPLOAD_URL = re.compile(r"/uploads/[A-Za-z0-9_./%-]+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_database() -> tuple[dict[str, int], int]:
    from database import connect

    counts: dict[str, int] = {}
    referenced: set[str] = set()
    with connect() as conn:
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        for table in tables:
            rows = conn.execute(f"SELECT * FROM `{table}`").fetchall()
            counts[table] = len(rows)
            for row in rows:
                for value in row.values():
                    if isinstance(value, str):
                        referenced.update(UPLOAD_URL.findall(value))

    missing = []
    for url in sorted(referenced):
        path = (ROOT / url.lstrip("/")).resolve()
        if UPLOAD_ROOT.resolve() not in path.parents or not path.is_file():
            missing.append(url)
    if missing:
        raise RuntimeError(f"{len(missing)} database upload references are missing; first: {missing[0]}")
    return counts, len(referenced)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    directory = args.output_dir.resolve()
    if directory == ROOT or ROOT in directory.parents:
        raise RuntimeError("Put migration exports outside the project and release archive")
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError(f"Migration output directory must be empty: {directory}")

    counts, referenced = inspect_database()
    files = sorted(path for path in UPLOAD_ROOT.rglob("*") if path.is_file())
    for path in files:
        if path.is_symlink() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
            raise RuntimeError(f"Upload escapes the upload directory: {path}")
    total_bytes = sum(path.stat().st_size for path in files)

    from database import export_backup_sql

    sql = export_backup_sql()
    directory.mkdir(parents=True, exist_ok=True)
    sql_path = directory / "tlhdd-mysql.sql"
    archive_path = directory / "tlhdd-uploads.tar"
    sql_path.write_bytes(sql)
    if os.name != "nt":
        sql_path.chmod(0o600)
    with tarfile.open(archive_path, "w") as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "database_counts": counts,
        "referenced_upload_urls": referenced,
        "upload_file_count": len(files),
        "upload_bytes": total_bytes,
        "mysql_sql": {"name": sql_path.name, "bytes": sql_path.stat().st_size, "sha256": sha256(sql_path)},
        "uploads_archive": {"name": archive_path.name, "bytes": archive_path.stat().st_size, "sha256": sha256(archive_path)},
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(files)} upload files ({total_bytes} bytes), {referenced} referenced URLs")
    print(f"Database counts: {counts}")
    print(f"Private migration output: {directory}")


if __name__ == "__main__":
    main()
