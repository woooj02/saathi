"""Saathi web server: the clinic pages, the patient pages and their small JSON API."""
import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import answers, gemini, mailer, nepali_dates, settings, store
from .answers_to_pdf import BadAnswer, build_values
from .filler import fill_pdf

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


# -- patient side -------------------------------------------------------------

def _load(form_id: str) -> dict:
    try:
        return store.load(form_id)
    except store.FormNotFound:
        raise HTTPException(404, "This form link isn't active.")


@app.get("/f/{form_id}")
def patient_page(form_id: str):
    return page("fill.html")


@app.get("/api/forms/{form_id}")
def get_form(form_id: str):
    form = _load(form_id)
    if form.get("status") != "published":
        raise HTTPException(404, "This form link isn't active.")
    return store.patient_view(form)


class Submission(BaseModel):
    answers: dict = Field(default_factory=dict)
    signer_name: str = Field(min_length=2, max_length=80)


class Spoken(BaseModel):
    question_id: str
    transcript: str = Field(max_length=2000)
    lang: str = "ne"


@app.post("/api/forms/{form_id}/interpret")
def interpret(form_id: str, body: Spoken):
    """A spoken or typed Nepali answer -> the English for the form (Gemini)."""
    form = _load(form_id)
    question = next((q for q in form["questions"] if q["id"] == body.question_id), None)
    if question is None:
        raise HTTPException(404, "No such question.")
    if not gemini.available():
        raise HTTPException(503, "AI is not configured; type or tap the answer instead.")
    try:
        return answers.interpret(question, body.transcript)
    except answers.NotInterpretable:
        raise HTTPException(422, "This question is answered by tapping.")
    except gemini.AIError:
        raise HTTPException(502, "Couldn't understand the answer right now.")


@app.post("/api/forms/{form_id}/submit")
def submit(form_id: str, body: Submission):
    form = _load(form_id)
    if form.get("status") != "published":
        raise HTTPException(404, "This form link isn't active.")
    name = " ".join(body.signer_name.split())
    if re.search(r"[\u0900-\u097F]", name):
        raise HTTPException(422, "Please type the name in English letters.")
    try:
        values, signature, skipped = build_values(form, body.answers, name)
    except BadAnswer as exc:
        raise HTTPException(422, str(exc))
    pdf = fill_pdf(store.original_pdf(form_id), values, signature)
    status = mailer.deliver(form, pdf, name, skipped)
    safe = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-") or "patient"
    return Response(pdf, media_type="application/pdf", headers={
        "X-Mail-Status": status,
        "Content-Disposition": f'attachment; filename="intake-{safe}.pdf"',
        "Access-Control-Expose-Headers": "X-Mail-Status",
    })


@app.get("/api/dates/convert")
def convert_date(calendar: str, year: int, month: int, day: int, fmt: str = "MM/DD/YYYY"):
    """A date from the picker, in either calendar, as the form wants it."""
    try:
        date = nepali_dates.to_date(calendar, year, month, day)
    except nepali_dates.BadDate as exc:
        raise HTTPException(422, str(exc))
    return {"value": nepali_dates.format_for_form(date, fmt), "en": nepali_dates.describe_en(date),
            "ne": nepali_dates.describe_ne(date, calendar)}


@app.get("/api/dates/bs-month-length")
def bs_month_length(year: int, month: int):
    try:
        return {"days": nepali_dates.bs_days_in_month(year, month)}
    except nepali_dates.BadDate as exc:
        raise HTTPException(422, str(exc))


@app.get("/")
def home():
    return RedirectResponse("/f/sample")


app.mount("/static", StaticFiles(directory=settings.WEB_DIR), name="static")
