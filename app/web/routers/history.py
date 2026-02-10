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

dict_repo = DictRepo()
mdx_service = MdxService(dict_repo)
vocab_service = VocabService(VocabRepo())

def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None

@router.get("/history", response_class=HTMLResponse)
def history_home(request: Request, dict_id: int | None = None, item_id: int | None = None):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    dicts = dict_repo.list_dicts()
    if dict_id is None and dicts:
        dict_id = dicts[0].id
    items = vocab_service.list_history(user.id, limit=200)

    selected = None
    if item_id is not None:
        for it in items:
            if it.id == item_id:
                selected = it; break
    if selected is None and items:
        selected = items[0]

    result, err = None, None
    if selected and dict_id:
        try:
            result = mdx_service.lookup(dict_id, selected.headword)
        except DictLookupError as e:
            err = str(e)

    return templates.TemplateResponse("history.html", {
        "request": request, "user": user, "dicts": dicts,
        "selected_dict_id": dict_id, "items": items,
        "selected_item": selected, "result": result, "error": err
    })

@router.post("/history/{item_id}/delete")
def delete_item(request: Request, item_id: int, dict_id: int = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    vocab_service.delete_history_item(item_id, user.id)
    return RedirectResponse(url=f"/history?dict_id={dict_id}", status_code=303)

@router.post("/history/clear")
def clear_all(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    vocab_service.clear_history(user.id)
    return RedirectResponse(url="/history", status_code=303)
