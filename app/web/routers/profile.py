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

@router.post("/me/password")
def change_password(
    request: Request,
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
):
    """Change password without requiring old password (per requirement)."""
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    if new_password != new_password_confirm:
        return templates.TemplateResponse(
            "profile.html",
            {"request": request, "user": user, "error": "Passwords do not match."},
            status_code=400,
        )

    try:
        user_service.change_password(user_id=user.id, new_password=new_password)
    except Exception as e:
        return templates.TemplateResponse(
            "profile.html",
            {"request": request, "user": user, "error": str(e)},
            status_code=400,
        )

    return RedirectResponse(url="/me", status_code=303)

@router.post("/me/delete")
def delete_self(request: Request):
    """Delete this user account (and all related data).

    The DB schema uses ON DELETE CASCADE for sessions/ideas/history/favourites,
    so deleting the `users` row removes everything automatically.
    """
    user, redirect = _require_user(request)
    if redirect:
        return redirect

    # Delete the user row (cascades)
    user_service.delete_self(user_id=user.id)

    # Clear cookie so the browser isn't left with a dead session token
    resp = RedirectResponse(url="/", status_code=303)
    from app.config import settings
    resp.delete_cookie(settings.SESSION_COOKIE_NAME)
    return resp
