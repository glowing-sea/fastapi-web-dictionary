from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Favourite:
    """A vocabulary-book entry.

    Favourites are global (not tied to a specific dictionary).
    The user can still choose which dictionary to *view* the definition in.
    """
    id: int
    user_id: int
    headword: str
    notes: str
    mastery: int
    created_at: str


@dataclass(frozen=True)
class HistoryItem:
    """A history entry.

    History is recorded per dictionary, because the same headword can
    have different definitions in different dictionaries.
    """
    id: int
    user_id: int
    dict_id: int
    headword: str
    created_at: str
