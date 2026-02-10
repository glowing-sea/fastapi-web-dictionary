from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Idea:
    id: int
    user_id: int
    title: str
    details: str
    created_at: str
