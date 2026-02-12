from __future__ import annotations

"""Service layer for user-related business logic.

This file intentionally contains *business rules* (validation, permissions)
and delegates persistence to the data layer (UserRepo).

Why this matters:
- Web layer (routers) stays thin: parse form inputs, call services, render templates.
- Service layer is testable without HTTP.
- Data layer is the only place that speaks SQL / sqlite3.
"""

from app.data.user_repo import UserRepo
from app.models.user import User
from app.service.security import hash_password


class UserService:
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    # ---------- normal user operations ----------

    def update_profile(self, user_id: int, display_name: str, bio: str) -> User:
        display_name, bio = display_name.strip(), bio.strip()

        if len(display_name) > 60:
            raise ValueError("Display name too long (max 60).")
        if len(bio) > 500:
            raise ValueError("Bio too long (max 500).")

        user = self.user_repo.update_profile(user_id, display_name, bio)
        if not user:
            raise ValueError("User not found.")
        return user

    def change_username(self, user_id: int, new_username: str) -> User:
        new_username = new_username.strip()

        if len(new_username) < 3:
            raise ValueError("Username must be at least 3 characters.")

        # Repo will raise sqlite UNIQUE constraint errors; we convert to a friendly message.
        try:
            user = self.user_repo.update_username(user_id, new_username)
        except Exception as e:
            raise ValueError("That username is already taken.") from e

        if not user:
            raise ValueError("User not found.")
        return user

    def change_password(self, user_id: int, new_password: str) -> None:
        """Change password without requiring the old password (as requested)."""
        new_password = new_password.strip()
        if len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        pw_hash = hash_password(new_password)
        self.user_repo.update_password_hash(user_id=user_id, new_password_hash=pw_hash)

    def delete_self(self, user_id: int) -> None:
        """Delete current user and all related data (via ON DELETE CASCADE)."""
        self.user_repo.delete_user(user_id=user_id)

    # ---------- admin operations ----------

    def admin_list_users(self) -> list[User]:
        return self.user_repo.list_users()

    def admin_delete_user(self, target_user_id: int) -> None:
        self.user_repo.delete_user(user_id=target_user_id)
