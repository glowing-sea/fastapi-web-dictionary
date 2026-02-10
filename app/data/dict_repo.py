from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.db.database import get_conn
from app.models.dictionary import Dictionary

class DictRepo:
    def list_dicts(self) -> List[Dictionary]:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, name, folder, mdx_filename, css_filename, cover_filename, created_at
                     FROM dictionaries ORDER BY name ASC"""
            ).fetchall()
        return [Dictionary(
            id=r["id"], name=r["name"], folder=r["folder"], mdx_filename=r["mdx_filename"],
            css_filename=r["css_filename"], cover_filename=r["cover_filename"], created_at=r["created_at"]
        ) for r in rows]

    def get_by_id(self, dict_id: int) -> Optional[Dictionary]:
        with get_conn() as conn:
            r = conn.execute(
                """SELECT id, name, folder, mdx_filename, css_filename, cover_filename, created_at
                     FROM dictionaries WHERE id = ?""",
                (dict_id,),
            ).fetchone()
        if not r:
            return None
        return Dictionary(
            id=r["id"], name=r["name"], folder=r["folder"], mdx_filename=r["mdx_filename"],
            css_filename=r["css_filename"], cover_filename=r["cover_filename"], created_at=r["created_at"]
        )

    def create(self, name: str, folder: str, mdx_filename: str, css_filename: str | None, cover_filename: str | None) -> Dictionary:
        now = datetime.now(timezone.utc).isoformat()
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO dictionaries (name, folder, mdx_filename, css_filename, cover_filename, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                (name, folder, mdx_filename, css_filename, cover_filename, now),
            )
            dict_id = int(cur.lastrowid)
            r = conn.execute(
                """SELECT id, name, folder, mdx_filename, css_filename, cover_filename, created_at
                     FROM dictionaries WHERE id = ?""",
                (dict_id,),
            ).fetchone()
        return Dictionary(
            id=r["id"], name=r["name"], folder=r["folder"], mdx_filename=r["mdx_filename"],
            css_filename=r["css_filename"], cover_filename=r["cover_filename"], created_at=r["created_at"]
        )

    def delete(self, dict_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM dictionaries WHERE id = ?", (dict_id,))
