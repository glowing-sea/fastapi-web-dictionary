from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import settings

def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect(settings.DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """Small helper for demo-style schema evolution."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def};")
    except sqlite3.OperationalError:
        pass

def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r["name"] == column for r in rows)

def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ).fetchone()
    return bool(row)

def _migrate_favourites_to_global(conn: sqlite3.Connection) -> None:
    """Bug fix (1): vocabulary should be global.

    Older versions had:
      favourites(user_id, dict_id, headword, ...)
    which makes the vocabulary book dictionary-specific.

    New schema:
      favourites(user_id, headword, ...)
    so a user favourites a *word* once, then can view it in any dictionary.

    SQLite can't drop columns/constraints easily, so we do:
      rename old table -> create new -> copy -> drop old
    """
    if not _table_exists(conn, "favourites"):
        return

    # Old schema indicator: dict_id column exists
    if not _table_has_column(conn, "favourites", "dict_id"):
        return  # already migrated

    conn.execute("ALTER TABLE favourites RENAME TO favourites_old;")

    conn.execute(
        """
        CREATE TABLE favourites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            headword TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, headword),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    # Copy + de-duplicate:
    # If the same user has the same headword in multiple dictionaries, we keep the
    # most recently created row's notes.
    rows = conn.execute(
        """
        SELECT user_id, headword, notes, created_at
        FROM favourites_old
        ORDER BY datetime(created_at) ASC
        """
    ).fetchall()

    for r in rows:
        conn.execute(
            """
            INSERT INTO favourites (user_id, headword, notes, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, headword)
            DO UPDATE SET notes=excluded.notes, created_at=excluded.created_at
            """,
            (r["user_id"], r["headword"], r["notes"], r["created_at"]),
        )

    conn.execute("DROP TABLE favourites_old;")

def init_db() -> None:
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.DICT_ROOT.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        # ---- Users ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        _try_add_column(conn, "users", "is_admin INTEGER NOT NULL DEFAULT 0")

        # ---- Sessions ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        # ---- Ideas ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        # ---- Dictionaries ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dictionaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                folder TEXT NOT NULL,
                mdx_filename TEXT NOT NULL,
                css_filename TEXT,
                cover_filename TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        # ---- Favourites (vocabulary book) ----
        # Create new schema if table doesn't exist; otherwise migrate older schema.
        if not _table_exists(conn, "favourites"):
            conn.execute(
                """
                CREATE TABLE favourites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    headword TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, headword),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
        else:
            _migrate_favourites_to_global(conn)

        # ---- History ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dict_id INTEGER NOT NULL,
                headword TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(dict_id) REFERENCES dictionaries(id) ON DELETE CASCADE
            );
            """
        )
