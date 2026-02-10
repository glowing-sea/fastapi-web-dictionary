from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user
from app.data.dict_repo import DictRepo
from app.data.vocab_repo import VocabRepo
from app.service.mdx_service import MdxService, DictLookupError
from app.service.vocab_service import VocabService

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

mdx_service = MdxService(DictRepo())
vocab_service = VocabService(VocabRepo())

def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None

@router.get("/dictionary", response_class=HTMLResponse)
def dictionary_home(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    dicts = mdx_service.list_dicts()
    return templates.TemplateResponse("dictionary.html", {
        "request": request, "user": user, "dicts": dicts,
        "selected_dict_id": dicts[0].id if dicts else None,
        "query": "", "result": None, "error": None
    })

@router.post("/dictionary/search", response_class=HTMLResponse)
def dictionary_search(request: Request, dict_id: int = Form(...), query: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    dicts = mdx_service.list_dicts()
    result, err = None, None
    try:
        result = mdx_service.lookup(dict_id, query)
        vocab_service.add_history(user.id, dict_id, result.headword)
    except DictLookupError as e:
        err = str(e)
    except Exception as e:
        err = f"Unexpected error: {e}"
    return templates.TemplateResponse("dictionary.html", {
        "request": request, "user": user, "dicts": dicts,
        "selected_dict_id": dict_id, "query": query, "result": result, "error": err
    }, status_code=200 if not err else 400)

@router.post("/dictionary/favourite")
def favourite_from_search(request: Request, dict_id: int = Form(...), headword: str = Form(...), notes: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        vocab_service.add_or_update_favourite(user.id, dict_id, headword, notes)
    except Exception:
        pass
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}&word={headword}", status_code=303)
