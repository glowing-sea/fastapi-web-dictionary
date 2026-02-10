from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user
from app.data.user_repo import UserRepo
from app.service.user_service import UserService

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
user_service = UserService(UserRepo())

def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None

@router.get("/me", response_class=HTMLResponse)
def me(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": None})

@router.post("/me/profile")
def update_profile(request: Request, display_name: str = Form(""), bio: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        user = user_service.update_profile(user.id, display_name, bio)
    except Exception as e:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": str(e)}, status_code=400)
    return RedirectResponse(url="/me", status_code=303)

@router.post("/me/username")
def change_username(request: Request, new_username: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        user = user_service.change_username(user.id, new_username)
    except Exception as e:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": str(e)}, status_code=400)
    return RedirectResponse(url="/me", status_code=303)
