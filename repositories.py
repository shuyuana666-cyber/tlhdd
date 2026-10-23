from __future__ import annotations

from typing import Any

from database import connect
from record_utils import normalize_records

def list_records(table: str, where: str = "", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM {table} {where} ORDER BY sort_order ASC, id ASC", params).fetchall()
    return normalize_records(rows)
