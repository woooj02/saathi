"""Saathi web server: the clinic pages, the patient pages and their small JSON API."""
import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import answers, converter, gemini, mailer, nepali_dates, settings, store
from .pdf_reader import NotAPdf, NotFillable, read_form
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


# -- clinic side --------------------------------------------------------------

MAX_PDF_BYTES = 15 * 1024 * 1024
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.get("/clinic")
def clinic_page():
    return page("clinic.html")


@app.get("/samples/pt-intake.pdf")
def sample_pdf():
    """The sample form, so a clinic (or a judge) can try the upload without their own PDF."""
    return FileResponse(settings.SAMPLES_DIR / "pt-intake" / "original.pdf", media_type="application/pdf",
                        filename="riverbend-pt-intake-sample.pdf")


def _clinic_form(form_id: str, edit_key: str | None) -> dict:
    form = _load(form_id)
    if form_id == store.SAMPLE_ID or not edit_key or edit_key != form.get("edit_key"):
        raise HTTPException(403, "This link can't edit that form.")
    return form


@app.post("/api/forms")
async def upload_form(clinic_name: str = Form(..., min_length=2, max_length=120),
                      clinic_email: str = Form(..., max_length=200),
                      pdf: UploadFile = File(...)):
    """Step 1 of setup: read the PDF's boxes (no AI, fast)."""
    clinic_email = clinic_email.strip()
    if not EMAIL_RE.match(clinic_email):
        raise HTTPException(422, "Please enter the clinic's email address.")
    data = await pdf.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "That PDF is larger than 15 MB.")
    try:
        read = read_form(data)
    except NotAPdf:
        raise HTTPException(400, "That file isn't a PDF. Please choose your intake form as a PDF.")
    except NotFillable:
        raise HTTPException(422, "This PDF has no fillable boxes. Saathi needs a fillable PDF form.")
    form = {"id": store.new_id(), "edit_key": store.new_edit_key(), "clinic_name": " ".join(clinic_name.split()),
            "clinic_email": clinic_email, "status": "reading", "source": "gemini", "questions": [], "consent": [],
            "pages": read["pages"], "box_count": len(read["fields"]), "file_name": pdf.filename}
    store.save(form, pdf=data)
    store.save_read(form["id"], read)
    return {"id": form["id"], "edit_key": form["edit_key"], "pages": read["pages"], "box_count": len(read["fields"])}


@app.post("/api/forms/{form_id}/convert")
def convert_form(form_id: str, x_edit_key: str = Header(None)):
    """Step 2 of setup: Gemini writes the English and Nepali questions (slow: tens of seconds)."""
    form = _clinic_form(form_id, x_edit_key)
    if not gemini.available():
        raise HTTPException(503, "AI is not configured on this server, so a new form can't be converted yet.")
    try:
        result = converter.convert(store.load_read(form_id))
    except gemini.AIError:
        raise HTTPException(502, "Converting the form didn't work this time. Please try again.")
    form.update(result)
    form["status"] = "draft"
    store.save(form)
    return store.clinic_view(form)


@app.get("/api/clinic/forms/{form_id}")
def clinic_form(form_id: str, x_edit_key: str = Header(None)):
    return store.clinic_view(_clinic_form(form_id, x_edit_key))


class Wording(BaseModel):
    questions: list[dict] = Field(default_factory=list)   # [{id, en?, ne?, help_ne?}]
    consent: list[dict] = Field(default_factory=list)     # [{id, ne?, title_ne?}]


@app.patch("/api/forms/{form_id}")
def edit_wording(form_id: str, body: Wording, x_edit_key: str = Header(None)):
    """The clinic fixes wording. Only text changes; which boxes a question fills stays as the PDF says."""
    form = _clinic_form(form_id, x_edit_key)
    by_id = {q["id"]: q for q in form["questions"]}
    for edit in body.questions:
        q = by_id.get(edit.get("id"))
        if not q:
            continue
        for key in ("en", "ne", "help_ne"):
            if isinstance(edit.get(key), str):
                q[key] = edit[key].strip()[:600]
        q.pop("needs_review", None)
    consent = {c["id"]: c for c in form["consent"]}
    for edit in body.consent:
        c = consent.get(edit.get("id"))
        for key in ("ne", "title_ne"):
            if c and isinstance(edit.get(key), str):
                c[key] = edit[key].strip()[:3000]
    store.save(form)
    return store.clinic_view(form)


@app.post("/api/forms/{form_id}/publish")
def publish(form_id: str, request: Request, x_edit_key: str = Header(None)):
    form = _clinic_form(form_id, x_edit_key)
    if not form["questions"]:
        raise HTTPException(409, "Convert the form before publishing it.")
    form["status"] = "published"
    store.save(form)
    base = settings.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return {"link": f"{base}/f/{form_id}"}


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


AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/aac", "audio/flac"}
MAX_AUDIO = 8 * 1024 * 1024   # about 30 s of speech is well under 1 MB


@app.post("/api/forms/{form_id}/interpret-audio")
async def interpret_audio(form_id: str, question_id: str = Form(...), audio: UploadFile = File(...)):
    """A recording of the patient's spoken answer -> the English for the form (Gemini listens to it)."""
    form = _load(form_id)
    question = next((q for q in form["questions"] if q["id"] == question_id), None)
    if question is None:
        raise HTTPException(404, "No such question.")
    if not gemini.available():
        raise HTTPException(503, "AI is not configured; type or tap the answer instead.")
    mime = (audio.content_type or "").split(";")[0].strip().lower()
    if mime not in AUDIO_TYPES:
        raise HTTPException(415, "Unsupported recording format.")
    data = await audio.read(MAX_AUDIO + 1)
    if not data:
        return {"ok": False}
    if len(data) > MAX_AUDIO:
        raise HTTPException(413, "The recording is too long.")
    try:
        return answers.interpret_audio(question, data, mime)
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
    return RedirectResponse("/clinic")


@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    """Browsers check scripts and styles for changes on every load, so an update is never half-applied."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=settings.WEB_DIR), name="static")
