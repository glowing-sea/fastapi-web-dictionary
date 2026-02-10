from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Tuple
from urllib.parse import quote, unquote

from app.config import settings
from app.data.dict_repo import DictRepo
from app.models.dictionary import Dictionary

try:
    from readmdict import MDX, MDD
except Exception:  # pragma: no cover
    MDX = None
    MDD = None


class DictLookupError(Exception):
    pass


@dataclass(frozen=True)
class EntryResult:
    """One matching entry returned by an MDX lookup.

    Bug fix (2): some dictionaries have *multiple* records for the same lookup key.
    We keep every matching record and render them all.
    """
    headword: str
    html: str


@dataclass(frozen=True)
class LookupResult:
    """Lookup output used by Dictionary, Vocabulary and History pages."""
    found: bool
    lookup_key: str
    entries: list[EntryResult]


class MdxService:

    def __init__(self, dict_repo: DictRepo):
        self.dict_repo = dict_repo

    def list_dicts(self) -> list[Dictionary]:
        return self.dict_repo.list_dicts()

    # ----------------------------
    # CSS detection (fixes: no-format dictionaries with only mdx+mdd)
    # ----------------------------
    def get_dict_css_asset(self, dict_id: int) -> str | None:
        """
        Many dictionaries (especially mdx+mdd only) expect a global CSS, but entry HTML
        does NOT include <link rel="stylesheet">. The CSS is often stored INSIDE the MDD.

        Priority:
        1) DB css_filename (if admin uploaded a real CSS file)
        2) extracted *.css on disk
        3) *.css packed inside *.mdd (choose style/main if present)
        """
        d = self.dict_repo.get_by_id(dict_id)
        if not d:
            return None

        # 1) Explicit CSS stored in DB
        if getattr(d, "css_filename", None):
            return str(d.css_filename).lstrip("/")

        base_dir = (settings.DICT_ROOT / d.folder).resolve()

        # 2) Any extracted CSS on disk
        css_files = list(base_dir.rglob("*.css"))
        if css_files:
            return str(css_files[0].relative_to(base_dir)).replace("\\", "/")

        # 3) Try CSS from MDD index
        for mdd_path in base_dir.rglob("*.mdd"):
            mdd_map = _get_mdd_map_cached(dict_id, str(mdd_path))
            css_keys = [k for k in mdd_map.keys() if k.lower().endswith(".css")]
            if not css_keys:
                continue

            # Prefer style.css / main.css if possible
            css_keys.sort(
                key=lambda k: (
                    "style" not in k.lower(),
                    "main" not in k.lower(),
                    len(k),
                )
            )
            return css_keys[0].lstrip("/")

        return None

    # ----------------------------
    # Lookup (fixes: @@@LINK redirects + "I"/"me" case issues)
    # ----------------------------
    
    def lookup(self, dict_id: int, word: str) -> LookupResult:
        """Look up a word in an installed MDX dictionary.

        Bug fix (2): some MDX dictionaries contain multiple records for the same key.
        For example, looking up "I" could yield multiple entries. We return *all* of them.
        """
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

        exact_map, casefold_map = _get_mdx_maps_cached(dict_id, str(mdx_path))

        # 1) Exact match first
        lookup_key = word
        vals = exact_map.get(lookup_key)

        # 2) Case-insensitive fallback (helps dictionaries where headwords are inconsistent)
        if vals is None:
            cf = word.casefold()
            mapped = casefold_map.get(cf)
            if mapped is not None:
                lookup_key = mapped
                vals = exact_map.get(lookup_key)

        if not vals:
            return LookupResult(found=False, lookup_key=word, entries=[])

        # Each value record might itself be a redirect via '@@@LINK=target'.
        # We resolve redirects, and if the resolved key has multiple values, we include them all.
        entries: list[EntryResult] = []
        seen: set[tuple[str, int]] = set()

        for v in vals:
            resolved_head, resolved_vals = self._resolve_mdx_link(exact_map, lookup_key, v)
            for rv in resolved_vals:
                key = (resolved_head, hash(rv))
                if key in seen:
                    continue
                seen.add(key)
                html = rewrite_mdx_html(dict_id, _safe_decode(rv))
                entries.append(EntryResult(headword=resolved_head, html=html))

        return LookupResult(found=True, lookup_key=lookup_key, entries=entries)

    def _resolve_mdx_link(
        self,
        exact_map: dict[str, list[bytes]],
        head: str,
        val_b: bytes,
    ) -> tuple[str, list[bytes]]:
        """Resolve MDX redirect records that contain '@@@LINK=target'.

        Many dictionaries store common headwords as redirects, e.g.:

            me
@@@LINK=mi

        We follow redirects up to a small depth to avoid infinite loops.

        Bug fix (2): the resolved key may have *multiple* values. We return them all.
        """
        seen: set[str] = set()
        cur_head = head
        cur_val = val_b

        for _ in range(10):  # max depth
            text = _safe_decode(cur_val)

            m = re.search(r"@@@LINK=(?P<target>.+)", text)
            if not m:
                return cur_head, [cur_val]

            target = m.group("target").strip()
            if not target or target in seen:
                return cur_head, [cur_val]

            seen.add(target)
            cur_head = target

            target_vals = exact_map.get(target)
            if not target_vals:
                return cur_head, [cur_val]

            # Continue resolving by inspecting the first value,
            # but if we finish, we'll return the full list.
            cur_val = target_vals[0]

        # if we hit max depth, return the current value
        return cur_head, [cur_val]

    def get_asset_bytes(self, dict_id: int, asset_path: str) -> Tuple[bytes, str]:
        """
        Serve an asset referenced by MDX HTML (img/css/js/audio).
        We try:
        1) extracted files on disk
        2) packed files inside any MDD
        """
        d = self.dict_repo.get_by_id(dict_id)
        if not d:
            raise DictLookupError("Dictionary not found.")

        # Normalize incoming path:
        # - decode %xx
        # - normalize slashes
        # - remove query/fragment
        asset_path = unquote(asset_path).replace("\\", "/")
        asset_path = asset_path.split("?", 1)[0].split("#", 1)[0]
        asset_path = asset_path.lstrip("/")

        base_dir = (settings.DICT_ROOT / d.folder).resolve()
        candidate = (base_dir / asset_path).resolve()

        # Prevent path traversal
        if not str(candidate).startswith(str(base_dir)):
            raise DictLookupError("Invalid asset path.")

        # 1) extracted file exists
        if candidate.exists() and candidate.is_file():
            data = candidate.read_bytes()
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            return data, mime

        # 2) try MDD
        if MDD is None:
            raise DictLookupError("Asset not found.")

        mdds = list(base_dir.rglob("*.mdd"))
        if not mdds:
            raise DictLookupError("Asset not found.")

        # Try a few variants because MDX and MDD keys are inconsistent about leading "/"
        key_candidates = [
            asset_path,
            asset_path.lstrip("/"),
            "/" + asset_path.lstrip("/"),
        ]

        for mdd_path in mdds:
            mdd_map = _get_mdd_map_cached(dict_id, str(mdd_path))

            for k in key_candidates:
                k_norm = k.replace("\\", "/").lstrip("/")
                if k_norm in mdd_map:
                    value = mdd_map[k_norm]
                    mime = mimetypes.guess_type(k_norm)[0] or "application/octet-stream"
                    return value, mime

        raise DictLookupError("Asset not found.")


# ----------------------------
# Caches
# ----------------------------
@lru_cache(maxsize=8)

@lru_cache(maxsize=8)
def _get_mdx_maps_cached(dict_id: int, mdx_path: str) -> tuple[dict[str, list[bytes]], dict[str, str]]:
    """Build lookup maps for an MDX file.

    Returns:
      - exact_map: headword -> list[bytes]   (Bug fix (2): keep *all* records for a key)
      - casefold_map: casefold(headword) -> a representative headword

    Why we build maps instead of calling mdx.lookup() every time:
      - mdx.lookup() is convenient but repeated calls are slower.
      - keeping our own map also lets us handle the "multiple values per key" bug.
    """
    mdx = MDX(mdx_path)
    exact: dict[str, list[bytes]] = {}
    casefold_map: dict[str, str] = {}

    for k, v in mdx.items():
        ks = _safe_decode(k)

        # Bug fix (2): store every record under the same key.
        exact.setdefault(ks, []).append(v)

        cf = ks.casefold()
        # keep first seen representative (stable)
        if cf not in casefold_map:
            casefold_map[cf] = ks

    return exact, casefold_map


@lru_cache(maxsize=32)
def _get_mdd_map_cached(dict_id: int, mdd_path: str) -> dict[str, bytes]:
    """
    Build an index of packed assets in MDD:
      normalized_key (no leading '/', forward slashes) -> bytes
    """
    mdd = MDD(mdd_path)
    out: dict[str, bytes] = {}

    for k, v in mdd.items():
        key = _safe_decode(k).replace("\\", "/")
        if key.startswith("./"):
            key = key[2:]
        key = key.lstrip("/")
        out[key] = v

    return out


def _safe_decode(b) -> str:
    if isinstance(b, str):
        return b
    # Chinese dictionaries commonly need big5/cp950
    for enc in ("utf-8", "utf-16", "gb18030", "big5", "cp950", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")


# ----------------------------
# HTML Rewriting
# - fixes sound:// by mapping to /dict_asset/...
# - fixes entry:// / bword:// by mapping to /dictionary/entry?...
# - fixes file:// paths
# ----------------------------
_ATTR_RE = re.compile(r'''(?P<attr>src|href)=(?P<q>["'])(?P<url>.*?)(?P=q)''', re.IGNORECASE)


def rewrite_mdx_html(dict_id: int, html: str) -> str:
    def repl(m):
        attr, q, url = m.group("attr"), m.group("q"), m.group("url").strip()

        if not url:
            return m.group(0)

        # If it is already a normal web URL or embedded data, keep it
        if url.startswith(("http://", "https://", "data:")):
            return m.group(0)

        # Handle sound:// which browsers cannot open directly
        if url.lower().startswith("sound://"):
            rel = url.split("sound://", 1)[1].lstrip("/").replace("\\", "/")
            return f'{attr}={q}/dict_asset/{dict_id}/{rel}{q}'

        # Internal entry links: entry://word, bword://word
        if url.lower().startswith(("entry://", "bword://")):
            target = url.split("://", 1)[1]
            target = target.strip()
            # route below will render entry in dictionary page
            return f'{attr}={q}/dictionary/entry?dict_id={dict_id}&q={quote(target)}{q}'

        # file:// references (common for css/img)
        url_norm = url
        if url_norm.startswith(("file:///", "file://")):
            url_norm = url_norm.split("file://", 1)[-1].lstrip("/")

        # normalize slashes, strip query/fragment, strip leading ./ and /
        url_norm = url_norm.replace("\\", "/")
        url_norm = url_norm.split("?", 1)[0].split("#", 1)[0]
        if url_norm.startswith("./"):
            url_norm = url_norm[2:]
        url_norm = url_norm.lstrip("/")

        if not url_norm or url_norm.startswith("#"):
            return m.group(0)

        return f'{attr}={q}/dict_asset/{dict_id}/{url_norm}{q}'

    return _ATTR_RE.sub(repl, html)
