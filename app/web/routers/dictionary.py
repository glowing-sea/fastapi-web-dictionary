from __future__ import annotations
from fastapi import APIRouter, Request, Form, Query
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


def _dict_css_url(dict_id: int | None) -> str | None:
    if dict_id is None:
        return None
    css_asset = mdx_service.get_dict_css_asset(dict_id)
    if not css_asset:
        return None
    return f"/dict_asset/{dict_id}/{css_asset}"


@router.get("/dictionary", response_class=HTMLResponse)
def dictionary_home(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = mdx_service.list_dicts()
    selected_dict_id = dicts[0].id if dicts else None

    return templates.TemplateResponse(
        "dictionary.html",
        {
            "request": request,
            "user": user,
            "dicts": dicts,
            "selected_dict_id": selected_dict_id,
            "dict_css_url": _dict_css_url(selected_dict_id),
            "query": "",
            "result": None,
            "error": None,
        },
    )


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

    return templates.TemplateResponse(
        "dictionary.html",
        {
            "request": request,
            "user": user,
            "dicts": dicts,
            "selected_dict_id": dict_id,
            "dict_css_url": _dict_css_url(dict_id),
            "query": query,
            "result": result,
            "error": err,
        },
        status_code=200 if not err else 400,
    )


@router.get("/dictionary/entry", response_class=HTMLResponse)
def dictionary_entry(request: Request, dict_id: int = Query(...), q: str = Query(...)):
    """
    This route is used by rewritten entry:// and bword:// links.
    It renders the dictionary page with the looked-up entry.
    """
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = mdx_service.list_dicts()

    result, err = None, None
    try:
        result = mdx_service.lookup(dict_id, q)
        vocab_service.add_history(user.id, dict_id, result.headword)
    except DictLookupError as e:
        err = str(e)
    except Exception as e:
        err = f"Unexpected error: {e}"

    return templates.TemplateResponse(
        "dictionary.html",
        {
            "request": request,
            "user": user,
            "dicts": dicts,
            "selected_dict_id": dict_id,
            "dict_css_url": _dict_css_url(dict_id),
            "query": q,
            "result": result,
            "error": err,
        },
        status_code=200 if not err else 400,
    )


@router.post("/dictionary/favourite")
def favourite_from_search(
    request: Request, dict_id: int = Form(...), headword: str = Form(...), notes: str = Form("")
):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        vocab_service.add_or_update_favourite(user.id, dict_id, headword, notes)
    except Exception:
        pass
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}&word={headword}", status_code=303)
