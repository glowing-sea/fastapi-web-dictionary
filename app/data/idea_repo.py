from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.db.database import get_conn
from app.models.idea import Idea

class IdeaRepo:
    def list_by_user(self, user_id: int) -> List[Idea]:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, user_id, title, details, created_at
                     FROM ideas WHERE user_id = ?
                     ORDER BY id DESC""",
                (user_id,),
            ).fetchall()
        return [Idea(id=r["id"], user_id=r["user_id"], title=r["title"], details=r["details"], created_at=r["created_at"]) for r in rows]

    def create(self, user_id: int, title: str, details: str) -> Idea:
        now = datetime.now(timezone.utc).isoformat()
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO ideas (user_id, title, details, created_at) VALUES (?, ?, ?, ?)",
                (user_id, title, details, now),
            )
            idea_id = int(cur.lastrowid)
            row = conn.execute("SELECT id, user_id, title, details, created_at FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        return Idea(id=row["id"], user_id=row["user_id"], title=row["title"], details=row["details"], created_at=row["created_at"])

    def get_by_id(self, idea_id: int) -> Optional[Idea]:
        with get_conn() as conn:
            row = conn.execute("SELECT id, user_id, title, details, created_at FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        if not row:
            return None
        return Idea(id=row["id"], user_id=row["user_id"], title=row["title"], details=row["details"], created_at=row["created_at"])

    def delete(self, idea_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
