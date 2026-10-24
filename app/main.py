"""Saathi web server: the clinic pages, the patient pages and their small JSON API."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import settings

app = FastAPI(title="Saathi")


@app.get("/api/health")
def health():
    return {"ok": True, "ai": bool(settings.GEMINI_API_KEY), "mail_mode": settings.MAIL_MODE}


app.mount("/static", StaticFiles(directory=settings.WEB_DIR), name="static")
