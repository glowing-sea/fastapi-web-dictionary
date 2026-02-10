from __future__ import annotations
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.database import init_db
from app.web.routers import home, auth, profile, ideas, dictionary, vocab, history, admin_dicts, dict_assets

app = FastAPI(title="Layered FastAPI Dictionary App")

@app.on_event("startup")
def on_startup() -> None:
    init_db()

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(ideas.router)

app.include_router(dictionary.router)
app.include_router(vocab.router)
app.include_router(history.router)

app.include_router(admin_dicts.router)
app.include_router(dict_assets.router)
