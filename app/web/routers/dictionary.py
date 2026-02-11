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
def dictionary_home(request: Request, dict_id: int | None = None, query: str = ""):
    """Dictionary search page (GET).

    Supports optional query+dict_id so we can redirect back here after favouriting
    without losing the current search.
    """
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = mdx_service.list_dicts()
    if not dicts:
        return templates.TemplateResponse(
            "dictionary.html",
            {"request": request, "user": user, "dicts": [], "selected_dict_id": None, "query": "", "result": None, "error": None, "favourite": None, "dict_css_url": ""},
        )

    selected_dict_id = dict_id or dicts[0].id

    result = None
    err = None
    favourite = None

    query = (query or "").strip()
    if query:
        try:
            result = mdx_service.lookup(dict_id=selected_dict_id, word=query)
        except Exception as e:
            err = str(e)
        # Always show favourite state for the query (even if not found in dictionary)
        favourite = vocab_service.get_favourite_by_word(user_id=user.id, headword=query)

    dict_css_url = _dict_css_url(selected_dict_id)

    return templates.TemplateResponse(
        "dictionary.html",
        {
            "request": request,
            "user": user,
            "dicts": dicts,
            "selected_dict_id": selected_dict_id,
            "query": query,
            "result": result,
            "error": err,
            "favourite": favourite,
            "dict_css_url": dict_css_url,
        },
    )



@router.post("/dictionary/search", response_class=HTMLResponse)
def dictionary_search(request: Request, dict_id: int = Form(...), query: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = mdx_service.list_dicts()

    query = (query or "").strip()
    result, err = None, None

    # Always compute favourite state based on the exact typed query (case-sensitive).
    favourite = vocab_service.get_favourite_by_word(user_id=user.id, headword=query) if query else None

    try:
        if query:
            result = mdx_service.lookup(dict_id=dict_id, word=query)
            # Record history using the exact typed query (case-sensitive).
            vocab_service.add_history(user.id, dict_id, query)
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
            "favourite": favourite,
        },
        status_code=200,
    )



@router.get("/dictionary/entry", response_class=HTMLResponse)
def dictionary_entry(request: Request, dict_id: int = Query(...), q: str = Query(...)):
    """Used by rewritten entry:// and bword:// links."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = mdx_service.list_dicts()

    q = (q or "").strip()
    result, err = None, None

    favourite = vocab_service.get_favourite_by_word(user_id=user.id, headword=q) if q else None

    try:
        if q:
            result = mdx_service.lookup(dict_id=dict_id, word=q)
            vocab_service.add_history(user.id, dict_id, q)
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
            "favourite": favourite,
        },
        status_code=200,
    )


@router.post("/dictionary/favourite")
def dictionary_favourite(
    request: Request,
    dict_id: int = Form(...),
    headword: str = Form(...),
    notes: str = Form(""),
    mastery: int = Form(1),
):
    """Add/update favourite for the current search word, then return to the dictionary page."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    try:
        mastery_int = int(mastery)
    except Exception:
        mastery_int = 1

    # This creates the favourite even if the dictionary lookup has no entry (custom vocab is allowed).
    vocab_service.add_or_update_favourite(
        user_id=user.id,
        headword=headword.strip(),
        notes=(notes or ""),
        mastery=mastery_int,
    )

    return RedirectResponse(url=f"/dictionary?dict_id={dict_id}&query={headword}", status_code=303)


@router.post("/dictionary/mastery_inc")
def dictionary_mastery_inc(request: Request, fav_id: int = Form(...), dict_id: int = Form(...), headword: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    fav = vocab_service.get_favourite(fav_id=fav_id, user_id=user.id)
    if fav:
        new_level = min(5, int(fav.mastery) + 1)
        vocab_service.update_mastery(fav_id=fav_id, user_id=user.id, mastery=new_level)
    return RedirectResponse(url=f"/dictionary?dict_id={dict_id}&query={headword}", status_code=303)


@router.post("/dictionary/mastery_dec")
def dictionary_mastery_dec(request: Request, fav_id: int = Form(...), dict_id: int = Form(...), headword: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    fav = vocab_service.get_favourite(fav_id=fav_id, user_id=user.id)
    if fav:
        new_level = max(1, int(fav.mastery) - 1)
        vocab_service.update_mastery(fav_id=fav_id, user_id=user.id, mastery=new_level)
    return RedirectResponse(url=f"/dictionary?dict_id={dict_id}&query={headword}", status_code=303)
@router.post("/dictionary/unfavourite")
def dictionary_unfavourite(
    request: Request,
    dict_id: int = Form(...),
    headword: str = Form(...),
    fav_id: int = Form(...),
):
    """Remove a favourite and return to the dictionary page."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    vocab_service.delete_favourite(fav_id=fav_id, user_id=user.id)
    return RedirectResponse(url=f"/dictionary?dict_id={dict_id}&query={headword}", status_code=303)
