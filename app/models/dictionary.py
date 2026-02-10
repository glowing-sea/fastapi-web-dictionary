from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Dictionary:
    id: int
    name: str
    folder: str
    mdx_filename: str
    css_filename: str | None
    cover_filename: str | None
    created_at: str
