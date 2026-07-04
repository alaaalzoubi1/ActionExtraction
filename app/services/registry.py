"""
registry.py – SQLite-backed class registry.

Schema:
  classes(name TEXT PK, required_fields TEXT, optional_fields TEXT)

The fine-tuned MiniLM model handles all label semantics internally —
no display_labels needed here.
"""
from __future__ import annotations
import sqlite3
import threading
from pathlib import Path
from app.models.schemas import ClassDefinition

_DB_PATH_DOCKER = Path("/app/data/classes.db")
_DB_PATH_LOCAL  = Path(__file__).resolve().parent.parent.parent / "data" / "classes.db"

_LOCK = threading.Lock()

# ── Default classes ───────────────────────────────────────────────────────────
# These names MUST match the labels used during fine-tuning.

_DEFAULTS: list[ClassDefinition] = [
    ClassDefinition(
        name="summary",
        required_fields=["lecture"],
        optional_fields=[],
    ),
    ClassDefinition(
        name="mcq",
        required_fields=["lecture"],
        optional_fields=["num_questions"],
    ),
    ClassDefinition(
        name="flashcard",
        required_fields=["lecture"],
        optional_fields=["num_cards"],
    ),
    ClassDefinition(
        name="tts",
        required_fields=["lecture"],
        optional_fields=["voice", "speed"],
    ),
    ClassDefinition(
        name="plan",
        required_fields=["start_date", "end_date"],
        optional_fields=["topics", "hours_per_day"],
    ),
    ClassDefinition(
        name="rag",
        required_fields=["query"],
        optional_fields=[],
    ),
]


def _db_path() -> Path:
    if _DB_PATH_DOCKER.parent.exists():
        return _DB_PATH_DOCKER
    _DB_PATH_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    return _DB_PATH_LOCAL


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_def(row: sqlite3.Row) -> ClassDefinition:
    return ClassDefinition(
        name=row["name"],
        required_fields=[f for f in row["required_fields"].split(",") if f],
        optional_fields=[f for f in row["optional_fields"].split(",") if f],
    )


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                name            TEXT PRIMARY KEY,
                required_fields TEXT NOT NULL DEFAULT '',
                optional_fields TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()
        if conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 0:
            for c in _DEFAULTS:
                _insert(conn, c)
            conn.commit()
        conn.close()


def _insert(conn: sqlite3.Connection, c: ClassDefinition) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO classes VALUES (?, ?, ?)",
        (c.name, ",".join(c.required_fields), ",".join(c.optional_fields)),
    )


def get_all() -> list[ClassDefinition]:
    with _LOCK:
        conn = _connect()
        rows = conn.execute("SELECT * FROM classes").fetchall()
        conn.close()
        return [_row_to_def(r) for r in rows]


def get(name: str) -> ClassDefinition | None:
    with _LOCK:
        conn = _connect()
        row  = conn.execute("SELECT * FROM classes WHERE name=?", (name,)).fetchone()
        conn.close()
        return _row_to_def(row) if row else None


def upsert(c: ClassDefinition) -> None:
    with _LOCK:
        conn = _connect()
        _insert(conn, c)
        conn.commit()
        conn.close()


def delete(name: str) -> bool:
    with _LOCK:
        conn = _connect()
        cur  = conn.execute("DELETE FROM classes WHERE name=?", (name,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0


def reset_to_defaults() -> None:
    with _LOCK:
        conn = _connect()
        conn.execute("DELETE FROM classes")
        conn.commit()
        for c in _DEFAULTS:
            _insert(conn, c)
        conn.commit()
        conn.close()


def list_names() -> list[str]:
    with _LOCK:
        conn = _connect()
        rows = conn.execute("SELECT name FROM classes").fetchall()
        conn.close()
        return [r["name"] for r in rows]
