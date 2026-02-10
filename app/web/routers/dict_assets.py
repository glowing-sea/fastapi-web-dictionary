from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import Response

from app.data.dict_repo import DictRepo
from app.service.mdx_service import MdxService, DictLookupError

router = APIRouter()
mdx_service = MdxService(DictRepo())

@router.get("/dict_asset/{dict_id}/{asset_path:path}")
def get_asset(dict_id: int, asset_path: str):
    try:
        data, mime = mdx_service.get_asset_bytes(dict_id, asset_path)
        return Response(content=data, media_type=mime)
    except DictLookupError as e:
        return Response(content=str(e), media_type="text/plain", status_code=404)
