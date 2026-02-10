from __future__ import annotations

from typing import Optional, Tuple
from datetime import datetime, timezone

from app.db.database import get_conn
from app.models.user import User

class UserRepo:
    def create_user(self, username: str, password_hash: str) -> User:
        now = datetime.now(timezone.utc).isoformat()
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO users (username, password_hash, created_at, is_admin)
                     VALUES (?, ?, ?, 0)""",
                (username, password_hash, now),
            )
            user_id = int(cur.lastrowid)
            row = conn.execute(
                """SELECT id, username, display_name, bio, created_at, is_admin
                     FROM users WHERE id = ?""",
                (user_id,),
            ).fetchone()

        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            bio=row["bio"],
            created_at=row["created_at"],
            is_admin=row["is_admin"],
        )

    def get_user_by_username_with_hash(self, username: str) -> Optional[Tuple[User, str]]:
        with get_conn() as conn:
            row = conn.execute(
                """SELECT id, username, password_hash, display_name, bio, created_at, is_admin
                     FROM users WHERE username = ?""",
                (username,),
            ).fetchone()
        if not row:
            return None
        user = User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            bio=row["bio"],
            created_at=row["created_at"],
            is_admin=row["is_admin"],
        )
        return user, row["password_hash"]

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with get_conn() as conn:
            row = conn.execute(
                """SELECT id, username, display_name, bio, created_at, is_admin
                     FROM users WHERE id = ?""",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            bio=row["bio"],
            created_at=row["created_at"],
            is_admin=row["is_admin"],
        )

    def update_profile(self, user_id: int, display_name: str, bio: str) -> Optional[User]:
        with get_conn() as conn:
            conn.execute("UPDATE users SET display_name = ?, bio = ? WHERE id = ?", (display_name, bio, user_id))
            row = conn.execute(
                """SELECT id, username, display_name, bio, created_at, is_admin FROM users WHERE id = ?""",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"], username=row["username"], display_name=row["display_name"],
            bio=row["bio"], created_at=row["created_at"], is_admin=row["is_admin"]
        )

    def update_username(self, user_id: int, new_username: str) -> Optional[User]:
        with get_conn() as conn:
            conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))
            row = conn.execute(
                """SELECT id, username, display_name, bio, created_at, is_admin FROM users WHERE id = ?""",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"], username=row["username"], display_name=row["display_name"],
            bio=row["bio"], created_at=row["created_at"], is_admin=row["is_admin"]
        )
