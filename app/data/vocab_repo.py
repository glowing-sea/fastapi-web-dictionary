from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.db.database import get_conn
from app.models.vocab import Favourite, HistoryItem

class VocabRepo:
    # -------------------------
    # Favourites (global vocab)
    # -------------------------
    def upsert_favourite(self, user_id: int, headword: str, notes: str) -> None:
        """Insert or update a favourite word.

        Bug fix (1): favourites are global, so the unique key is (user_id, headword).
        """
        now = datetime.now(timezone.utc).isoformat()
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO favourites (user_id, headword, notes, created_at)
                     VALUES (?, ?, ?, ?)
                     ON CONFLICT(user_id, headword)
                     DO UPDATE SET notes=excluded.notes, created_at=excluded.created_at""",
                (user_id, headword, notes, now),
            )

    def list_favourites(self, user_id: int) -> List[Favourite]:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, user_id, headword, notes, created_at
                     FROM favourites
                     WHERE user_id = ?
                     ORDER BY headword COLLATE NOCASE ASC""",
                (user_id,),
            ).fetchall()

        return [
            Favourite(
                id=r["id"],
                user_id=r["user_id"],
                headword=r["headword"],
                notes=r["notes"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def get_favourite(self, fav_id: int, user_id: int) -> Optional[Favourite]:
        with get_conn() as conn:
            r = conn.execute(
                """SELECT id, user_id, headword, notes, created_at
                     FROM favourites
                     WHERE id = ? AND user_id = ?""",
                (fav_id, user_id),
            ).fetchone()

        if not r:
            return None

        return Favourite(
            id=r["id"],
            user_id=r["user_id"],
            headword=r["headword"],
            notes=r["notes"],
            created_at=r["created_at"],
        )

    def delete_favourite(self, fav_id: int, user_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM favourites WHERE id = ? AND user_id = ?", (fav_id, user_id))

    def update_favourite_notes(self, fav_id: int, user_id: int, notes: str) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE favourites SET notes = ? WHERE id = ? AND user_id = ?",
                (notes, fav_id, user_id),
            )

    # -------------
    # History
    # -------------
    def add_history(self, user_id: int, dict_id: int, headword: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO history (user_id, dict_id, headword, created_at) VALUES (?, ?, ?, ?)",
                (user_id, dict_id, headword, now),
            )

    def list_history(self, user_id: int, limit: int = 200) -> List[HistoryItem]:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, user_id, dict_id, headword, created_at
                     FROM history
                     WHERE user_id = ?
                     ORDER BY id DESC
                     LIMIT ?""",
                (user_id, limit),
            ).fetchall()

        return [
            HistoryItem(
                id=r["id"],
                user_id=r["user_id"],
                dict_id=r["dict_id"],
                headword=r["headword"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def delete_history_item(self, item_id: int, user_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM history WHERE id = ? AND user_id = ?", (item_id, user_id))

    def clear_history(self, user_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
