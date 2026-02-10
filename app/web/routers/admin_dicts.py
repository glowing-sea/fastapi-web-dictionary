from __future__ import annotations
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user, is_admin
from app.data.dict_repo import DictRepo
from app.service.dict_install_service import DictInstallService, DictInstallError

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

dict_repo = DictRepo()
install_service = DictInstallService(dict_repo)

def _require_admin(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    if not is_admin(user):
        return user, RedirectResponse(url="/", status_code=303)
    return user, None

@router.get("/admin/dicts", response_class=HTMLResponse)
def admin_dicts_page(request: Request):
    user, redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_dicts.html", {"request": request, "user": user, "dicts": dict_repo.list_dicts(), "error": None})

@router.post("/admin/dicts/upload")
async def upload_dict(request: Request, name: str = Form(...), zip_file: UploadFile = File(...)):
    user, redirect = _require_admin(request)
    if redirect:
        return redirect
    try:
        data = await zip_file.read()
        install_service.install_from_zip_bytes(name, data)
        return RedirectResponse(url="/admin/dicts", status_code=303)
    except DictInstallError as e:
        return templates.TemplateResponse("admin_dicts.html", {"request": request, "user": user, "dicts": dict_repo.list_dicts(), "error": str(e)}, status_code=400)
    except Exception as e:
        return templates.TemplateResponse("admin_dicts.html", {"request": request, "user": user, "dicts": dict_repo.list_dicts(), "error": f"Unexpected error: {e}"}, status_code=500)

@router.post("/admin/dicts/{dict_id}/delete")
def delete_dict(request: Request, dict_id: int):
    user, redirect = _require_admin(request)
    if redirect:
        return redirect
    install_service.delete_dictionary(dict_id)
    return RedirectResponse(url="/admin/dicts", status_code=303)
