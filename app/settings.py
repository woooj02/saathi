"""Settings from .env (see .env.example). Read once at import."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("SAATHI_DATA_DIR", ROOT / "data"))
FORMS_DIR = DATA_DIR / "forms"
OUTBOX_DIR = DATA_DIR / "outbox"
SAMPLES_DIR = Path(os.getenv("SAATHI_SAMPLES_DIR", ROOT / "samples"))
WEB_DIR = ROOT / "web"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
# tried in order when the main model is busy or out of its free daily quota (each model has its own)
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_FALLBACK_MODELS",
    "gemini-3.5-flash,gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-flash-lite-latest",
).split(",") if m.strip()]

MAIL_MODE = os.getenv("MAIL_MODE", "file").strip().lower()
SMTP_HOST = os.getenv("SMTP_HOST", "smtppro.zoho.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "Saathi <contact@keepsrunning.com>")
MIN_SEND_GAP_SECONDS = int(os.getenv("MIN_SEND_GAP_SECONDS", "300"))

# Patient links are built from this when set (e.g. on a deployed server), else from the request.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

for d in (FORMS_DIR, OUTBOX_DIR):
    d.mkdir(parents=True, exist_ok=True)
