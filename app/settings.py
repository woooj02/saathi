"""Settings from .env (see .env.example). Read once at import."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("SAATHI_DATA_DIR", ROOT / "data"))
FORMS_DIR = DATA_DIR / "forms"
OUTBOX_DIR = DATA_DIR / "outbox"
SAMPLES_DIR = ROOT / "samples"
WEB_DIR = ROOT / "web"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

MAIL_MODE = os.getenv("MAIL_MODE", "file").strip().lower()
SMTP_HOST = os.getenv("SMTP_HOST", "smtppro.zoho.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "Saathi <contact@keepsrunning.com>")
MIN_SEND_GAP_SECONDS = int(os.getenv("MIN_SEND_GAP_SECONDS", "300"))

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8010").rstrip("/")

for d in (FORMS_DIR, OUTBOX_DIR):
    d.mkdir(parents=True, exist_ok=True)
