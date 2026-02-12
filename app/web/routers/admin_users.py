
from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user, is_admin
from app.data.user_repo import UserRepo
from app.service.user_service import UserService

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

user_service = UserService(UserRepo())

def _require_admin(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    if not is_admin(user):
        return user, RedirectResponse(url="/", status_code=303)
    return user, None

@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request):
    admin, redirect = _require_admin(request)
    if redirect:
        return redirect

    users = user_service.admin_list_users()
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "user": admin, "users": users, "error": None},
    )

@router.post("/admin/users/{user_id}/delete")
def admin_delete_user(request: Request, user_id: int):
    admin, redirect = _require_admin(request)
    if redirect:
        return redirect

    # Allow deleting any user (including self). If you delete yourself, your session will be invalid.
    user_service.admin_delete_user(target_user_id=user_id)

    return RedirectResponse(url="/admin/users", status_code=303)
