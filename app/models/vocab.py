from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Favourite:
    id: int
    user_id: int
    dict_id: int
    headword: str
    notes: str
    created_at: str

@dataclass(frozen=True)
class HistoryItem:
    id: int
    user_id: int
    dict_id: int
    headword: str
    created_at: str
