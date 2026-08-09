"""Sync Postgres adapter mimicking sqlite3 enough for CrmStore / OutreachStore.

Uses SQLAlchemy create_engine with postgresql+psycopg://.
Translates ``?`` placeholders to ``%s``. Skips PRAGMA foreign_keys.
Implements PRAGMA table_info via information_schema.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Result

_ENGINE: Engine | None = None
_PRAGMA_TABLE_INFO = re.compile(
    r"^\s*PRAGMA\s+table_info\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*$",
    re.IGNORECASE,
)


def async_url_to_sync(url: str) -> str:
    """Convert postgresql+asyncpg:// (or bare) to postgresql+psycopg://."""
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + u[len("postgresql+asyncpg://") :]
    if u.startswith("postgres+asyncpg://"):
        return "postgresql+psycopg://" + u[len("postgres+asyncpg://") :]
    if u.startswith("postgresql://"):
        return "postgresql+psycopg://" + u[len("postgresql://") :]
    if u.startswith("postgres://"):
        return "postgresql+psycopg://" + u[len("postgres://") :]
    if "+psycopg" in u or "+psycopg2" in u:
        return u
    return u


def os_environ_database_url() -> str:
    return (
        os.environ.get("KEPRIX_TEST_DATABASE_URL")
        or os.environ.get("KEPRIX_DATABASE_URL")
        or ""
    )


def database_url_sync() -> str:
    env = (os_environ_database_url() or "").strip()
    if env:
        return async_url_to_sync(env)
    try:
        from keprix.config.settings import get_settings

        return async_url_to_sync(get_settings().database_url)
    except Exception:
        return ""


def get_sync_engine(*, url: str | None = None, force_new: bool = False) -> Engine | None:
    global _ENGINE
    target = async_url_to_sync(url) if url else database_url_sync()
    if not target:
        return None
    if force_new or _ENGINE is None or str(_ENGINE.url) not in target:
        _ENGINE = create_engine(target, pool_pre_ping=True, future=True)
    return _ENGINE


def ping_postgres(url: str | None = None) -> bool:
    try:
        engine = get_sync_engine(url=url, force_new=bool(url))
        if engine is None:
            return False
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def translate_placeholders(sql: str) -> str:
    """Replace sqlite ``?`` bind markers with psycopg ``%s`` (outside quotes).

    Literal ``%`` (e.g. LIKE patterns) must become ``%%`` for psycopg.
    """
    out: list[str] = []
    i = 0
    in_single = False
    in_double = False
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if ch == "?" and not in_single and not in_double:
            out.append("%s")
            i += 1
            continue
        if ch == "%":
            out.append("%%")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


class PgRow:
    """sqlite3.Row-like mapping (index by name or integer)."""

    __slots__ = ("_data", "_keys")

    def __init__(self, mapping: dict[str, Any]) -> None:
        self._data = dict(mapping)
        self._keys = list(mapping.keys())

    def keys(self) -> list[str]:
        return list(self._keys)

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return self._data[self._keys[key]]
        return self._data[key]

    def __iter__(self):
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __repr__(self) -> str:
        return f"PgRow({self._data!r})"


class PgCursor:
    def __init__(self, result: Result | None, rows: list[PgRow] | None = None) -> None:
        self._result = result
        self._rows = rows
        self._idx = 0
        if rows is None and result is not None:
            try:
                mappings = result.mappings().all()
                self._rows = [PgRow(dict(m)) for m in mappings]
            except Exception:
                self._rows = []

    def fetchone(self) -> PgRow | None:
        if not self._rows or self._idx >= len(self._rows):
            return None
        row = self._rows[self._idx]
        self._idx += 1
        return row

    def fetchall(self) -> list[PgRow]:
        if not self._rows:
            return []
        remaining = self._rows[self._idx :]
        self._idx = len(self._rows)
        return list(remaining)

    def __iter__(self):
        return iter(self.fetchall())


class PgConnection:
    """Minimal sqlite3.Connection stand-in for CRM/outreach stores."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._conn: Connection = engine.connect()
        self.row_factory = None  # accepted for API parity

    def execute(self, sql: str, params: Sequence[Any] | tuple = ()) -> PgCursor:
        statement = (sql or "").strip()
        if not statement:
            return PgCursor(None, rows=[])

        if statement.upper().startswith("PRAGMA FOREIGN_KEYS"):
            return PgCursor(None, rows=[])

        m = _PRAGMA_TABLE_INFO.match(statement)
        if m:
            table = m.group(1)
            return self._pragma_table_info(table)

        # INSERT OR IGNORE -> ON CONFLICT DO NOTHING (idempotent-ish)
        if re.search(r"\bINSERT\s+OR\s+IGNORE\b", statement, re.IGNORECASE):
            statement = re.sub(
                r"\bINSERT\s+OR\s+IGNORE\b",
                "INSERT",
                statement,
                count=1,
                flags=re.IGNORECASE,
            )
            if "ON CONFLICT" not in statement.upper():
                statement = statement.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

        translated = translate_placeholders(statement)
        result = self._conn.exec_driver_sql(translated, tuple(params or ()))
        return PgCursor(result)

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> PgCursor:
        last: PgCursor | None = None
        for params in seq_of_params:
            last = self.execute(sql, tuple(params))
        return last or PgCursor(None, rows=[])

    def executescript(self, script: str) -> None:
        for stmt in _split_sql_statements(script):
            if stmt:
                self.execute(stmt)
        self.commit()

    def _pragma_table_info(self, table: str) -> PgCursor:
        result = self._conn.execute(
            text(
                """
                SELECT ordinal_position AS cid,
                       column_name AS name,
                       data_type AS type,
                       CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                       column_default AS dflt_value,
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM information_schema.key_column_usage k
                           JOIN information_schema.table_constraints tc
                             ON tc.constraint_name = k.constraint_name
                            AND tc.table_schema = k.table_schema
                           WHERE tc.constraint_type = 'PRIMARY KEY'
                             AND k.table_name = columns.table_name
                             AND k.column_name = columns.column_name
                             AND k.table_schema = columns.table_schema
                       ) THEN 1 ELSE 0 END AS pk
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table
                ORDER BY ordinal_position
                """
            ),
            {"table": table},
        )
        rows = []
        for m in result.mappings().all():
            rows.append(
                PgRow(
                    {
                        0: m["cid"],
                        1: m["name"],
                        2: m["type"],
                        3: m["notnull"],
                        4: m["dflt_value"],
                        5: m["pk"],
                        "cid": m["cid"],
                        "name": m["name"],
                        "type": m["type"],
                        "notnull": m["notnull"],
                        "dflt_value": m["dflt_value"],
                        "pk": m["pk"],
                    }
                )
            )
        # CrmStore uses row[1] for name; ensure integer index works
        fixed: list[PgRow] = []
        for r in rows:
            data = {
                "cid": r["cid"],
                "name": r["name"],
                "type": r["type"],
                "notnull": r["notnull"],
                "dflt_value": r["dflt_value"],
                "pk": r["pk"],
            }
            # Also expose positional via custom row
            fixed.append(_PositionalRow(data))
        return PgCursor(None, rows=fixed)  # type: ignore[arg-type]

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


class _PositionalRow(PgRow):
    """Row that supports both name and 0..5 positional access like sqlite PRAGMA."""

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            order = ("cid", "name", "type", "notnull", "dflt_value", "pk")
            return self._data[order[key]]
        return self._data[key]


def _split_sql_statements(script: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    for ch in script:
        if ch == "'":
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == ";" and not in_single:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def connect_crm_pg(url: str | None = None) -> PgConnection:
    engine = get_sync_engine(url=url)
    if engine is None:
        raise RuntimeError("KEPRIX_DATABASE_URL is not configured for CRM Postgres")
    return PgConnection(engine)


def reset_sync_engine_for_tests() -> None:
    global _ENGINE
    if _ENGINE is not None:
        try:
            _ENGINE.dispose()
        except Exception:
            pass
    _ENGINE = None
