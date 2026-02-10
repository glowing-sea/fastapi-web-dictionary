from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.database import get_conn

class SessionRepo:
    SESSION_LIFETIME_HOURS = 24

    def create_session(self, user_id: int, token: str) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.SESSION_LIFETIME_HOURS)
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO sessions (token, user_id, created_at, expires_at)
                     VALUES (?, ?, ?, ?)""",
                (token, user_id, now.isoformat(), expires.isoformat()),
            )

    def get_user_id_by_token(self, token: str) -> Optional[int]:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            self.delete_session(token)
            return None
        return int(row["user_id"])

    def delete_session(self, token: str) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
