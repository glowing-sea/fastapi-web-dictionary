from __future__ import annotations
import json
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user
from app.data.dict_repo import DictRepo
from app.data.vocab_repo import VocabRepo
from app.service.mdx_service import MdxService, DictLookupError
from app.service.vocab_service import VocabService

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

dict_repo = DictRepo()
mdx_service = MdxService(dict_repo)
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


@router.get("/vocab", response_class=HTMLResponse)
def vocab_home(request: Request, dict_id: int | None = None, fav_id: int | None = None, word: str | None = None):
    """Vocabulary book page.

    Bug fix:
    - favourites must always be defined (previous version only defined it when dict_id was None),
      which crashed when clicking a word (e.g. /vocab?dict_id=2&fav_id=1).
    """
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    dicts = dict_repo.list_dicts()
    if dict_id is None and dicts:
        dict_id = dicts[0].id

    # In this version of the app, favourites are *global* (not per-dictionary).
    favourites = vocab_service.list_favourites(user.id)

    selected = vocab_service.get_favourite(fav_id, user.id) if fav_id is not None else None
    if selected is None and word and favourites:
        for f in favourites:
            if f.headword == word:
                selected = f
                break

    result, err = None, None
    if selected and dict_id:
        try:
            result = mdx_service.lookup(dict_id, selected.headword)
        except DictLookupError as e:
            err = str(e)

    return templates.TemplateResponse(
        "vocab.html",
        {
            "request": request,
            "user": user,
            "dicts": dicts,
            "selected_dict_id": dict_id,
            "dict_css_url": _dict_css_url(dict_id),
            "favourites": favourites,
            "selected_fav": selected,
            "result": result,
            "error": err,
        },
    )


@router.post("/vocab/{fav_id}/delete")
def delete_fav(request: Request, fav_id: int, dict_id: int = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    vocab_service.delete_favourite(fav_id, user.id)
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}", status_code=303)


@router.post("/vocab/{fav_id}/notes")
def update_notes(request: Request, fav_id: int, dict_id: int = Form(...), notes: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        vocab_service.update_notes(fav_id, user.id, notes)
    except Exception:
        pass
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}&fav_id={fav_id}", status_code=303)

@router.post("/vocab/clear")
def clear_all_favs(request: Request, dict_id: int = Form(...)):
    """Delete all favourites in the selected dictionary."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    vocab_service.delete_all_favourites(user_id=user.id)
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}", status_code=303)

@router.get("/vocab/export")
def export_vocab(request: Request, dict_id: int):
    """Export favourites as JSON (word + notes)."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    favs = vocab_service.list_favourites(user.id)
    payload = [{"word": f.headword, "notes": f.notes} for f in favs]
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    filename = f"vocabulary_dict_{dict_id}.json"
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post("/vocab/import")
async def import_vocab(request: Request, dict_id: int = Form(...), json_file: UploadFile = File(...)):
    """Import favourites from uploaded JSON file.

    If a favourite already exists, its notes are overwritten.
    """
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    raw = await json_file.read()
    try:
        items = json.loads(raw.decode("utf-8"))
        if not isinstance(items, list):
            raise ValueError("JSON must be a list.")
    except Exception:
        return RedirectResponse(url=f"/vocab?dict_id={dict_id}", status_code=303)

    vocab_service.import_favourites(user_id=user.id, items=items)
    return RedirectResponse(url=f"/vocab?dict_id={dict_id}", status_code=303)
