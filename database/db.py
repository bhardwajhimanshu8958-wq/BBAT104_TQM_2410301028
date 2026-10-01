"""
database/db.py — SQLite connection helper for the Parking Management System.

Provides:
- get_connection()  : context manager that opens, yields, and closes a connection.
- init_db()         : reads schema.sql and creates all tables on first run.
- query_db()        : convenience wrapper for SELECT queries → list[dict].
- execute_db()      : convenience wrapper for INSERT / UPDATE / DELETE.

Why SQLite: zero-configuration, file-based, sufficient for a single-operator
desktop system.  All tables are created with CHECK constraints so the DB itself
enforces data integrity regardless of which code path writes to it.
"""

import sqlite3
import contextlib
from pathlib import Path

from config import DB_PATH, SCHEMA_PATH


@contextlib.contextmanager
def get_connection():
    """Open a SQLite connection with foreign-key enforcement enabled.

    Yields the connection so callers can use it in a `with` block.
    Commits automatically on success; rolls back on any exception.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows accessible as dicts
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables from schema.sql if they do not already exist.

    Safe to call every time the app starts — uses CREATE TABLE IF NOT EXISTS.
    """
    schema = Path(SCHEMA_PATH).read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)


def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT statement and return rows as a list of dicts.

    Args:
        sql:    A SELECT SQL string with optional ? placeholders.
        params: Tuple of values to bind to the placeholders.

    Returns:
        List of rows, each row is a plain dict keyed by column name.
    """
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def execute_db(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT, UPDATE, or DELETE statement.

    Args:
        sql:    A DML SQL string with optional ? placeholders.
        params: Tuple of values to bind.

    Returns:
        The lastrowid for INSERT statements; 0 otherwise.
    """
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid or 0
