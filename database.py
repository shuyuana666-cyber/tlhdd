"""MySQL database access for the Tonglihua site.

The small DB-API adapter keeps the existing application query helpers readable
while using PyMySQL and MySQL 8 exclusively at runtime.
"""

from __future__ import annotations

import os
import re
import logging
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pymysql
from cache_service import changes_public_data, invalidate_public_cache
from pymysql.cursors import DictCursor

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.mysql.sql"
IntegrityError = pymysql.err.IntegrityError
DatabaseError = pymysql.MySQLError

class DbRow(dict[str, Any]):
    """Dictionary row that also supports DB-API positional access."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)

def _convert_placeholders(sql: str, params: Any) -> str:
    """Convert qmark and colon-named placeholders outside quoted SQL text."""
    if params is None:
        return sql

    named = isinstance(params, Mapping)
    out: list[str] = []
    i = 0
    quote = ""
    while i < len(sql):
        char = sql[i]
        if quote:
            out.append(char)
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    out.append(sql[i + 1])
                    i += 1
                else:
                    quote = ""
            elif char == "\\" and quote in {"'", '"'} and i + 1 < len(sql):
                out.append(sql[i + 1])
                i += 1
            i += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
            out.append(char)
            i += 1
            continue
        if char == "-" and sql[i:i + 2] == "--":
            end = sql.find("\n", i)
            if end < 0:
                out.append(sql[i:])
                break
            out.append(sql[i:end + 1])
            i = end + 1
            continue
        if char == "/" and sql[i:i + 2] == "/*":
            end = sql.find("*/", i + 2)
            if end < 0:
                out.append(sql[i:])
                break
            out.append(sql[i:end + 2])
            i = end + 2
            continue
        if named and char == ":" and i + 1 < len(sql) and (sql[i + 1].isalpha() or sql[i + 1] == "_"):
            match = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", sql[i:])
            if match:
                out.append(f"%({match.group(1)})s")
                i += len(match.group(0))
                continue
        if not named and char == "?":
            out.append("%s")
        else:
            out.append(char)
        i += 1
    return "".join(out)

class QueryResult:
    def __init__(self, cursor: Any):
        self._cursor = cursor
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount
        if cursor.description is None:
            cursor.close()
            self._cursor = None

    @staticmethod
    def _row(value: Any) -> DbRow | None:
        return DbRow(value) if value is not None else None

    def fetchone(self) -> DbRow | None:
        if self._cursor is None:
            return None
        return self._row(self._cursor.fetchone())

    def fetchall(self) -> list[DbRow]:
        if self._cursor is None:
            return []
        rows = [DbRow(row) for row in self._cursor.fetchall()]
        self._cursor.close()
        self._cursor = None
        return rows

    def fetchmany(self, size: int | None = None) -> list[DbRow]:
        if self._cursor is None:
            return []
        rows = [DbRow(row) for row in self._cursor.fetchmany(size)]
        return rows

    def close(self) -> None:
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None

class DatabaseConnection:
    def __init__(self) -> None:
        host = os.environ.get("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = int(os.environ.get("MYSQL_PORT", "3306"))
        database = os.environ.get("MYSQL_DATABASE", "tlhdd").strip() or "tlhdd"
        user = os.environ.get("MYSQL_USER", "tlhdd_app").strip() or "tlhdd_app"
        password = os.environ.get("MYSQL_PASSWORD", "")
        if not password:
            raise RuntimeError("MYSQL_PASSWORD must be set before starting the application")
        options: dict[str, Any] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": False,
            "connect_timeout": int(os.environ.get("MYSQL_CONNECT_TIMEOUT", "10")),
            "read_timeout": int(os.environ.get("MYSQL_READ_TIMEOUT", "30")),
            "write_timeout": int(os.environ.get("MYSQL_WRITE_TIMEOUT", "30")),
            "init_command": "SET time_zone = '+00:00'",
        }
        ssl_ca = os.environ.get("MYSQL_SSL_CA", "").strip()
        if ssl_ca:
            options["ssl"] = {"ca": ssl_ca}
        self._connection = pymysql.connect(**options)
        self._public_dirty = False

    def __enter__(self) -> DatabaseConnection:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if exc_type is None:
                self._connection.commit()
                if self._public_dirty:
                    invalidate_public_cache()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()

    def execute(self, sql: str, params: Any = None) -> QueryResult:
        cursor = self._connection.cursor()
        started = time.perf_counter()
        try:
            cursor.execute(_convert_placeholders(sql, params), params)
        except Exception:
            cursor.close()
            raise
        finally:
            self._log_slow(sql, started)
        self._public_dirty |= changes_public_data(sql)
        return QueryResult(cursor)

    def executemany(self, sql: str, params: Sequence[Sequence[Any]]) -> QueryResult:
        cursor = self._connection.cursor()
        started = time.perf_counter()
        try:
            cursor.executemany(_convert_placeholders(sql, params[0] if params else None), params)
        except Exception:
            cursor.close()
            raise
        finally:
            self._log_slow(sql, started)
        self._public_dirty |= changes_public_data(sql)
        return QueryResult(cursor)

    @staticmethod
    def _log_slow(sql: str, started: float) -> None:
        elapsed = (time.perf_counter() - started) * 1000
        try:
            threshold = float(os.environ.get("TLHDD_SLOW_SQL_MS", "200"))
        except ValueError:
            threshold = 200
        if threshold > 0 and elapsed >= threshold:
            # Identify query shape without logging SQL literals or customer values.
            import hashlib
            fingerprint = hashlib.sha256(sql.encode()).hexdigest()[:12]
            operation = sql.strip().split()[0].upper() if sql.strip() else "UNKNOWN"
            logging.getLogger(__name__).warning("Slow SQL op=%s fingerprint=%s duration_ms=%.1f", operation, fingerprint, elapsed)

def connect() -> DatabaseConnection:
    return DatabaseConnection()

def initialize_schema() -> None:
    """Apply checked-in MySQL DDL and create missing secondary indexes."""
    if not SCHEMA_PATH.is_file():
        raise RuntimeError(f"MySQL schema file is missing: {SCHEMA_PATH}")
    statements = [part.strip() for part in SCHEMA_PATH.read_text(encoding="utf-8").split(";") if part.strip()]
    with connect() as conn:
        version_row = conn.execute("SELECT VERSION() AS version").fetchone()
        version = str(version_row["version"] if version_row else "")
        if "mariadb" in version.lower():
            raise RuntimeError("This project requires Oracle MySQL 8.0.16 or newer; MariaDB is not supported")
        version_match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if not version_match or tuple(map(int, version_match.groups())) < (8, 0, 16):
            raise RuntimeError(f"MySQL 8.0.16 or newer is required (connected server reports {version or 'unknown'})")
        for statement in statements:
            match = re.match(r"CREATE\s+INDEX\s+(\w+)\s+ON\s+(\w+)\b", statement, re.IGNORECASE)
            if match:
                index_name, table_name = match.group(1), match.group(2)
                exists = conn.execute(
                    """SELECT 1 FROM information_schema.statistics
                       WHERE table_schema = DATABASE() AND table_name = ? AND index_name = ? LIMIT 1""",
                    (table_name, index_name),
                ).fetchone()
                if exists:
                    continue
            conn.execute(statement)

def export_backup_sql() -> bytes:
    """Create a logical backup, excluding credentials for active sessions."""
    statements = [part.strip() for part in SCHEMA_PATH.read_text(encoding="utf-8").split(";") if part.strip()]
    table_statements = [statement for statement in statements if re.match(r"CREATE\s+TABLE\b", statement, re.IGNORECASE)]
    index_statements = [statement for statement in statements if re.match(r"CREATE\s+INDEX\b", statement, re.IGNORECASE)]
    table_names = [re.match(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", statement, re.IGNORECASE).group(1) for statement in table_statements]
    output: list[str] = ["-- Tonglihua MySQL logical backup\nSET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n"]
    with connect() as conn:
        existing_tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        for table in reversed(table_names):
            if table in existing_tables:
                output.append(f"DROP TABLE IF EXISTS `{table}`;\n")
        for statement in table_statements + index_statements:
            output.append(statement.rstrip(";") + ";\n")
        for table in table_names:
            if table in {"admin_sessions", "public_sessions"}:
                continue
            columns = [row[0] for row in conn.execute(f"SHOW COLUMNS FROM `{table}`").fetchall()]
            col_sql = ", ".join(f"`{column}`" for column in columns)
            rows = conn.execute(f"SELECT * FROM `{table}`").fetchall()
            for row in rows:
                values = ", ".join(_sql_literal(row[column]) for column in columns)
                output.append(f"INSERT INTO `{table}` ({col_sql}) VALUES ({values});\n")
        output.append("SET FOREIGN_KEY_CHECKS=1;\n")
    return "".join(output).encode("utf-8")

def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "X'" + bytes(value).hex() + "'"
    encoded = str(value).encode("utf-8").hex()
    return f"CONVERT(X'{encoded}' USING utf8mb4)"
