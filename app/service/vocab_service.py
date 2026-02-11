from __future__ import annotations

from typing import List, Optional

from app.data.vocab_repo import VocabRepo
from app.models.vocab import Favourite, HistoryItem


class VocabService:
    """Service layer for favourites + history.

    Keep validation/business logic here; keep SQL in VocabRepo.
    """

    def __init__(self, repo: VocabRepo):
        self.repo = repo

    # -------------------------
    # Favourites (global vocab)
    # -------------------------
    def add_or_update_favourite(self, user_id: int, headword: str, notes: str, mastery: int = 1, created_at: str | None = None) -> None:
        headword = headword.strip()
        if not headword:
            raise ValueError("Headword cannot be empty.")
        if not (1 <= mastery <= 5):
            raise ValueError('Mastery must be 1..5.')
        if len(notes) > 2000:
            raise ValueError("Notes too long (max 2000).")
        self.repo.upsert_favourite(user_id, headword, notes.strip(), mastery, created_at=created_at)

    def list_favourites(self, user_id: int) -> List[Favourite]:
        return self.repo.list_favourites(user_id)

    def get_favourite(self, fav_id: int, user_id: int) -> Optional[Favourite]:
        return self.repo.get_favourite(fav_id, user_id)

    def get_favourite_by_word(self, user_id: int, headword: str) -> Optional[Favourite]:
        return self.repo.get_favourite_by_word(user_id=user_id, headword=headword)

    def delete_favourite(self, fav_id: int, user_id: int) -> None:
        self.repo.delete_favourite(fav_id, user_id)

    def delete_all_favourites(self, user_id: int) -> None:
        self.repo.delete_all_favourites(user_id)

    def update_mastery(self, fav_id: int, user_id: int, mastery: int) -> None:
        if not (1 <= mastery <= 5):
            raise ValueError('Mastery must be 1..5.')
        self.repo.update_favourite_mastery(fav_id, user_id, mastery)

    def update_notes(self, fav_id: int, user_id: int, notes: str) -> None:
        if len(notes) > 2000:
            raise ValueError("Notes too long (max 2000).")
        self.repo.update_favourite_notes(fav_id, user_id, notes.strip())



    def import_favourites(self, user_id: int, items: list[dict]) -> int:
        """Import favourites from JSON list.

        Expected items: [{"word": "...", "notes": "..."}]
        Existing words have their notes overwritten.
        """
        count = 0
        for it in items:
            word = str(it.get("word", "")).strip()
            notes = str(it.get("notes", "")).strip()
            mastery = int(it.get("mastery", 1) or 1)
            created_at = it.get("created_at")
            if not word:
                continue
            self.add_or_update_favourite(user_id=user_id, headword=word, notes=notes, mastery=mastery, created_at=created_at)
            count += 1
        return count

    # -------------
    # History
    # -------------
    def add_history(self, user_id: int, dict_id: int, headword: str) -> None:
        headword = headword.strip()
        if headword:
            self.repo.add_history(user_id, dict_id, headword)

    def list_history(self, user_id: int, limit: int = 200) -> List[HistoryItem]:
        return self.repo.list_history(user_id, limit)

    def delete_history_item(self, item_id: int, user_id: int) -> None:
        self.repo.delete_history_item(item_id, user_id)

    def clear_history(self, user_id: int) -> None:
        self.repo.clear_history(user_id)
