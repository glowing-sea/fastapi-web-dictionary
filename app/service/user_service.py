from __future__ import annotations
from app.data.user_repo import UserRepo
from app.models.user import User

class UserService:
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

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
        try:
            user = self.user_repo.update_username(user_id, new_username)
        except Exception as e:
            raise ValueError("That username is already taken.") from e
        if not user:
            raise ValueError("User not found.")
        return user
