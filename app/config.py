from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    DB_PATH: Path = Path(__file__).resolve().parent.parent / "app.db"
    SESSION_COOKIE_NAME: str = "session_token"
    DICT_ROOT: Path = Path(__file__).resolve().parent / "dictionaries"

settings = Settings()
