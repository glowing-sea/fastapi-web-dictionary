from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_user
from app.data.idea_repo import IdeaRepo
from app.service.idea_service import IdeaService

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
idea_service = IdeaService(IdeaRepo())

def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None

@router.get("/ideas", response_class=HTMLResponse)
def list_ideas(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    ideas = idea_service.list_my_ideas(user.id)
    return templates.TemplateResponse("ideas.html", {"request": request, "user": user, "ideas": ideas, "error": None})

@router.post("/ideas")
def create_idea(request: Request, title: str = Form(...), details: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        idea_service.create_idea(user.id, title, details)
    except Exception as e:
        ideas = idea_service.list_my_ideas(user.id)
        return templates.TemplateResponse("ideas.html", {"request": request, "user": user, "ideas": ideas, "error": str(e)}, status_code=400)
    return RedirectResponse(url="/ideas", status_code=303)

@router.post("/ideas/{idea_id}/delete")
def delete_idea(request: Request, idea_id: int):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        idea_service.delete_idea(user.id, idea_id)
    except PermissionError as e:
        ideas = idea_service.list_my_ideas(user.id)
        return templates.TemplateResponse("ideas.html", {"request": request, "user": user, "ideas": ideas, "error": str(e)}, status_code=403)
    return RedirectResponse(url="/ideas", status_code=303)
