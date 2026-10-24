"""Saathi web server: the clinic pages, the patient pages and their small JSON API."""
import json
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import settings

app = FastAPI(title="Saathi")


def page(name: str) -> FileResponse:
    return FileResponse(settings.WEB_DIR / name, headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    return {"ok": True, "ai": bool(settings.GEMINI_API_KEY), "mail_mode": settings.MAIL_MODE}


# -- speech test page (build step 1, dev only) --------------------------------

@app.get("/lab")
def lab_page():
    return page("lab.html")


@app.post("/api/lab/results")
async def lab_results(request: Request):
    body = await request.json()
    body["saved_at"] = datetime.now(timezone.utc).isoformat()
    path = settings.DATA_DIR / "lab-results.json"
    runs = json.loads(path.read_text()) if path.exists() else []
    runs.append(body)
    path.write_text(json.dumps(runs, ensure_ascii=False, indent=2))
    return {"ok": True, "runs": len(runs)}


@app.get("/")
def home():
    return RedirectResponse("/lab")


app.mount("/static", StaticFiles(directory=settings.WEB_DIR), name="static")
