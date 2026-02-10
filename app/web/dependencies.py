from __future__ import annotations
from typing import Optional
from fastapi import Request
from app.config import settings
from app.data.session_repo import SessionRepo
from app.data.user_repo import UserRepo
from app.models.user import User

session_repo = SessionRepo()
user_repo = UserRepo()

def get_current_user(request: Request) -> Optional[User]:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    user_id = session_repo.get_user_id_by_token(token)
    if user_id is None:
        return None
    return user_repo.get_user_by_id(user_id)

def is_admin(user: Optional[User]) -> bool:
    return bool(user and user.is_admin)
