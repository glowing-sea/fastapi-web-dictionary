from __future__ import annotations

import re, shutil, zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.data.dict_repo import DictRepo
from app.models.dictionary import Dictionary

class DictInstallError(Exception): pass

def _safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:80] or "dictionary"

class DictInstallService:
    def __init__(self, dict_repo: DictRepo):
        self.dict_repo = dict_repo

    def install_from_zip_bytes(self, name: str, zip_bytes: bytes) -> Dictionary:
        name = name.strip()
        if len(name) < 2:
            raise DictInstallError("Dictionary name is too short.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        folder_name = f"{_safe_name(name)}_{stamp}"
        target_dir = settings.DICT_ROOT / folder_name
        target_dir.mkdir(parents=True, exist_ok=False)

        try:
            zip_path = target_dir / "upload.zip"
            zip_path.write_bytes(zip_bytes)
            with zipfile.ZipFile(zip_path, "r") as z:
                for member in z.namelist():
                    if Path(member).is_absolute() or ".." in Path(member).parts:
                        raise DictInstallError("ZIP contains unsafe paths.")
                z.extractall(target_dir)
            zip_path.unlink(missing_ok=True)

            mdx_files = list(target_dir.rglob("*.mdx"))
            if len(mdx_files) != 1:
                raise DictInstallError("ZIP must contain exactly one .mdx file.")
            mdx_path = mdx_files[0]

            css_files = list(target_dir.rglob("*.css"))
            css_path = css_files[0] if css_files else None

            image_files = []
            for ext in ("*.png","*.jpg","*.jpeg","*.webp","*.gif"):
                image_files.extend(target_dir.rglob(ext))
            cover_path = None
            for cand in image_files:
                if cand.name.lower().startswith(("cover","icon","logo")):
                    cover_path = cand; break
            if cover_path is None and image_files:
                cover_path = image_files[0]

            rel_folder = folder_name
            mdx_rel = str(mdx_path.relative_to(target_dir))
            css_rel = str(css_path.relative_to(target_dir)) if css_path else None
            cover_rel = str(cover_path.relative_to(target_dir)) if cover_path else None

            return self.dict_repo.create(name, rel_folder, mdx_rel, css_rel, cover_rel)

        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

    def delete_dictionary(self, dict_id: int) -> None:
        d = self.dict_repo.get_by_id(dict_id)
        if not d:
            return
        shutil.rmtree(settings.DICT_ROOT / d.folder, ignore_errors=True)
        self.dict_repo.delete(dict_id)
