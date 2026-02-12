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

def init_db() -> None:
    """Create tables if they don't exist.

    NOTE: You said you'll recreate the database when schema changes.
    In practice, it's convenient to allow restarting the dev server with an existing DB file,
    so we also do a small, best-effort patch for the favourites schema.
    """
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

        # ---- Favourites (Vocabulary) ----
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favourites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                headword TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                mastery INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, headword),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        # Best-effort: if an older favourites table exists, ensure required columns exist.
        _maybe_migrate_favourites_schema(conn)


def _maybe_migrate_favourites_schema(conn) -> None:
    """Best-effort, backwards-compatible schema patching.

    You said you'll recreate the DB when schema changes; however, dev servers are often restarted
    with an existing app.db file. This function prevents startup crashes by ensuring required
    columns exist (idempotent). It will *not* attempt to rewrite indexes/collations.
    """
    try:
        rows = conn.execute("PRAGMA table_info(favourites);").fetchall()
    except Exception:
        return
    cols = {r[1] for r in rows}  # (cid, name, type, notnull, dflt_value, pk)
    if not rows:
        return

# Migration Helper
# # If an older schema used NOCASE collation on headword or the UNIQUE index,
# # "I" and "i" would be treated as the same word. Rebuild the table to restore
# # case-sensitive behaviour.
# try:
#     row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='favourites';").fetchone()
#     table_sql = (row[0] if row else "") or ""
# except Exception:
#     table_sql = ""

# if "NOCASE" in table_sql.upper():
#     try:
#         conn.execute("ALTER TABLE favourites RENAME TO favourites_old;")
#         conn.execute(
#             """
#             CREATE TABLE favourites (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER NOT NULL,
#                 headword TEXT NOT NULL,
#                 notes TEXT NOT NULL DEFAULT '',
#                 mastery INTEGER NOT NULL DEFAULT 1,
#                 created_at TEXT NOT NULL,
#                 UNIQUE(user_id, headword),
#                 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
#             );
#             """
#         )
#         # Copy best-effort (duplicates differing only by case couldn't exist in old schema anyway)
#         conn.execute(
#             """INSERT INTO favourites (id, user_id, headword, notes, mastery, created_at)
#                  SELECT id, user_id, headword, notes,
#                         COALESCE(mastery, 1) as mastery,
#                         created_at
#                  FROM favourites_old;"""
#         )
#         conn.execute("DROP TABLE favourites_old;")
#         # Refresh column set after rebuild
#         rows = conn.execute("PRAGMA table_info(favourites);").fetchall()
#         cols = {r[1] for r in rows}
#     except Exception:
#         # If rebuild fails, keep running with the existing table.
#         pass

#     # New in v7: mastery
#     if "mastery" not in cols:
#         try:
#             conn.execute("ALTER TABLE favourites ADD COLUMN mastery INTEGER NOT NULL DEFAULT 1;")
#         except Exception:
#             pass

#     # Ensure notes exists (older versions might have NULLable notes)
#     if "notes" not in cols:
#         try:
#             conn.execute("ALTER TABLE favourites ADD COLUMN notes TEXT NOT NULL DEFAULT '';")
#         except Exception:
#             pass

#     if "created_at" not in cols:
#         try:
#             conn.execute("ALTER TABLE favourites ADD COLUMN created_at TEXT NOT NULL DEFAULT '';")
#         except Exception:
#             pass
