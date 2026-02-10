from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    id: int
    username: str
    display_name: str
    bio: str
    created_at: str
    is_admin: int
