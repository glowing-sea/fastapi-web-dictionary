from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import Response

from app.data.dict_repo import DictRepo
from app.service.mdx_service import MdxService, DictLookupError

router = APIRouter()
mdx_service = MdxService(DictRepo())

_CSS_OVERRIDE = '\n/* WebDict override: allow selecting/copying text inside dictionary definition area.\n   Many MDX dictionaries ship CSS that disables selection for IPA/pronunciation spans. */\n.definition, .definition * {\n  -webkit-user-select: text !important;\n  user-select: text !important;\n  -webkit-touch-callout: default !important;\n}\n'.encode("utf-8")

@router.get("/dict_asset/{dict_id}/{asset_path:path}")
def get_asset(dict_id: int, asset_path: str):
    """Serve assets referenced by MDX HTML.

    Bug fix:
    - IPA/pronunciation text in some dictionaries (e.g. OALD9) is not selectable because the
      dictionary's own CSS disables user selection. Since dictionary CSS is loaded *after* our
      app CSS, global overrides in /static/style.css may lose.

      Solution: when serving any .css asset, append a tiny override CSS at the END of the file.
      This keeps dictionary styling but re-enables selection/copy for text.
    """
    try:
        data, mime = mdx_service.get_asset_bytes(dict_id, asset_path)

        # If this is a CSS file, append our override at the end so it wins in the cascade.
        if asset_path.lower().endswith(".css") or (mime and mime.startswith("text/css")):
            if not data.endswith(b"\n"):
                data += b"\n"
            data += _CSS_OVERRIDE
            mime = "text/css"

        return Response(content=data, media_type=mime)
    except DictLookupError as e:
        return Response(content=str(e), media_type="text/plain", status_code=404)
