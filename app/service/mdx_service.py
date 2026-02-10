from __future__ import annotations

import mimetypes, re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from app.config import settings
from app.data.dict_repo import DictRepo
from app.models.dictionary import Dictionary

try:
    from readmdict import MDX, MDD
except Exception:  # pragma: no cover
    MDX = None
    MDD = None

class DictLookupError(Exception): pass

@dataclass(frozen=True)
class LookupResult:
    found: bool
    headword: str
    html: str

class MdxService:
    def __init__(self, dict_repo: DictRepo):
        self.dict_repo = dict_repo

    def list_dicts(self) -> list[Dictionary]:
        return self.dict_repo.list_dicts()

    def lookup(self, dict_id: int, word: str) -> LookupResult:
        word = word.strip()
        if not word:
            raise DictLookupError("Please enter a word.")
        d = self.dict_repo.get_by_id(dict_id)
        if not d:
            raise DictLookupError("Dictionary not found.")
        if MDX is None:
            raise DictLookupError("Missing dependency: readmdict. Run: pip install -r requirements.txt")

        mdx_path = settings.DICT_ROOT / d.folder / d.mdx_filename
        if not mdx_path.exists():
            raise DictLookupError("MDX file missing on server.")

        # mdx = _get_mdx_cached(dict_id, str(mdx_path))
        # items = mdx.lookup(word)
        # if not items:
        #     return LookupResult(found=False, headword=word, html="<p><em>Not found.</em></p>")

        # head_b, val_b = items[0]
        # head = _safe_decode(head_b)
        # html = rewrite_mdx_html(dict_id, _safe_decode(val_b))
        # return LookupResult(found=True, headword=head, html=html)

        mdx_map = _get_mdx_map_cached(dict_id, str(mdx_path))  # NEW
        val_b = mdx_map.get(word)
        if not val_b:
            return LookupResult(found=False, headword=word, html="<p><em>Not found.</em></p>")

        html = rewrite_mdx_html(dict_id, _safe_decode(val_b))
        return LookupResult(found=True, headword=word, html=html)  # word is the headword used




    def get_asset_bytes(self, dict_id: int, asset_path: str) -> Tuple[bytes, str]:
        d = self.dict_repo.get_by_id(dict_id)
        if not d:
            raise DictLookupError("Dictionary not found.")
        base_dir = (settings.DICT_ROOT / d.folder).resolve()
        candidate = (base_dir / asset_path).resolve()
        if not str(candidate).startswith(str(base_dir)):
            raise DictLookupError("Invalid asset path.")
        if candidate.exists() and candidate.is_file():
            data = candidate.read_bytes()
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            return data, mime

        # try mdd
        if MDD is None:
            raise DictLookupError("Asset not found.")
        mdds = list(base_dir.rglob("*.mdd"))
        if not mdds:
            raise DictLookupError("Asset not found.")
        key_candidates = [asset_path, asset_path.lstrip("/"), "/" + asset_path.lstrip("/")]
        for mdd_path in mdds:
            # mdd = _get_mdd_cached(dict_id, str(mdd_path))
            # for k in key_candidates:
            #     found = mdd.lookup(k)
            #     if found:
            #         _, value = found[0]
            #         mime = mimetypes.guess_type(k)[0] or "application/octet-stream"
            #         return value, mime

            mdd_map = _get_mdd_map_cached(dict_id, str(mdd_path))  # NEW
            for k in key_candidates:
                k_norm = k.lstrip("/")
                if k_norm in mdd_map:
                    value = mdd_map[k_norm]
                    mime = mimetypes.guess_type(k_norm)[0] or "application/octet-stream"
                    return value, mime

        raise DictLookupError("Asset not found.")


@lru_cache(maxsize=8)
def _get_mdx_map_cached(dict_id: int, mdx_path: str) -> dict[str, bytes]:
    mdx = MDX(mdx_path)
    # Build a Python dict: headword(str) -> definition(bytes)
    # This is memory-heavy for huge dictionaries, but simple and reliable.
    return {_safe_decode(k): v for k, v in mdx.items()}

@lru_cache(maxsize=32)
def _get_mdd_map_cached(dict_id: int, mdd_path: str) -> dict[str, bytes]:
    mdd = MDD(mdd_path)
    # MDD items are like: (filename_bytes, content_bytes)
    # Store filenames without a leading "/" for easier matching.
    return {_safe_decode(k).lstrip("/"): v for k, v in mdd.items()}


def _safe_decode(b) -> str:
    if isinstance(b, str):
        return b
    for enc in ("utf-8","utf-16","gb18030","latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")

@lru_cache(maxsize=8)
def _get_mdx_cached(dict_id: int, mdx_path: str):
    return MDX(mdx_path)

@lru_cache(maxsize=32)
def _get_mdd_cached(dict_id: int, mdd_path: str):
    return MDD(mdd_path)

_ATTR_RE = re.compile(r'''(?P<attr>src|href)=(?P<q>["'])(?P<url>.*?)(?P=q)''', re.IGNORECASE)

def rewrite_mdx_html(dict_id: int, html: str) -> str:
    def repl(m):
        attr, q, url = m.group("attr"), m.group("q"), m.group("url").strip()
        if url.startswith(("http://","https://","data:","entry://","sound://","bword://")):
            return m.group(0)
        url_norm = url[2:] if url.startswith("./") else url
        if not url_norm:
            return m.group(0)
        new_url = f"/dict_asset/{dict_id}/{url_norm.lstrip('/')}"
        return f"{attr}={q}{new_url}{q}"
    return _ATTR_RE.sub(repl, html)
