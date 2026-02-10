from __future__ import annotations
import secrets
from dataclasses import dataclass

from app.data.user_repo import UserRepo
from app.data.session_repo import SessionRepo
from app.models.user import User
from app.service.security import hash_password, verify_password

class AuthError(Exception): pass

@dataclass
class AuthResult:
    user: User
    session_token: str

class AuthService:
    def __init__(self, user_repo: UserRepo, session_repo: SessionRepo):
        self.user_repo = user_repo
        self.session_repo = session_repo

    def register(self, username: str, password: str) -> AuthResult:
        username = username.strip()
        if len(username) < 3:
            raise AuthError("Username must be at least 3 characters.")
        if len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")
        pw_hash = hash_password(password)
        try:
            user = self.user_repo.create_user(username=username, password_hash=pw_hash)
        except Exception as e:
            raise AuthError("That username is already taken.") from e
        token = secrets.token_urlsafe(32)
        self.session_repo.create_session(user_id=user.id, token=token)
        return AuthResult(user=user, session_token=token)

    def login(self, username: str, password: str) -> AuthResult:
        found = self.user_repo.get_user_by_username_with_hash(username.strip())
        if not found:
            raise AuthError("Invalid username or password.")
        user, stored_hash = found
        if not verify_password(password, stored_hash):
            raise AuthError("Invalid username or password.")
        token = secrets.token_urlsafe(32)
        self.session_repo.create_session(user_id=user.id, token=token)
        return AuthResult(user=user, session_token=token)

    def logout(self, token: str) -> None:
        self.session_repo.delete_session(token)
