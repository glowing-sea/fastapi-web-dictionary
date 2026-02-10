from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.data.user_repo import UserRepo
from app.data.session_repo import SessionRepo
from app.service.auth_service import AuthService, AuthError

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
auth_service = AuthService(UserRepo(), SessionRepo())

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": None})

@router.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        result = auth_service.register(username, password)
    except AuthError as e:
        return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": str(e)}, status_code=400)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(settings.SESSION_COOKIE_NAME, result.session_token, httponly=True, samesite="lax")
    return resp

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})

@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        result = auth_service.login(username, password)
    except AuthError as e:
        return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": str(e)}, status_code=400)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(settings.SESSION_COOKIE_NAME, result.session_token, httponly=True, samesite="lax")
    return resp

@router.post("/logout")
def logout(request: Request):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        auth_service.logout(token)
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(settings.SESSION_COOKIE_NAME)
    return resp
