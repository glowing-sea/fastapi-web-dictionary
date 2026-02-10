from __future__ import annotations
from typing import List
from app.data.idea_repo import IdeaRepo
from app.models.idea import Idea

class IdeaService:
    def __init__(self, idea_repo: IdeaRepo):
        self.idea_repo = idea_repo

    def list_my_ideas(self, user_id: int) -> List[Idea]:
        return self.idea_repo.list_by_user(user_id)

    def create_idea(self, user_id: int, title: str, details: str) -> Idea:
        title, details = title.strip(), details.strip()
        if not title:
            raise ValueError("Title cannot be empty.")
        return self.idea_repo.create(user_id, title, details)

    def delete_idea(self, user_id: int, idea_id: int) -> None:
        idea = self.idea_repo.get_by_id(idea_id)
        if not idea:
            return
        if idea.user_id != user_id:
            raise PermissionError("You cannot delete someone else's idea.")
        self.idea_repo.delete(idea_id)
