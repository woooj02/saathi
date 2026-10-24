"""Form Store: one folder per form under data/forms/<id>/ with original.pdf and form.json.

The sample form lives in samples/pt-intake/ and is always served as id "sample",
so the patient journey can be tried and recorded without converting anything.
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from . import settings

SAMPLE_ID = "sample"
ID_RE = re.compile(r"^[a-z0-9]{6,32}$")


class FormNotFound(Exception):
    pass


def _folder(form_id: str) -> Path:
    if form_id == SAMPLE_ID:
        return settings.SAMPLES_DIR / "pt-intake"
    if not ID_RE.match(form_id):
        raise FormNotFound(form_id)
    return settings.FORMS_DIR / form_id


def new_id() -> str:
    return secrets.token_hex(5)   # 10 hex chars: short enough to read out, hard to guess


def load(form_id: str) -> dict:
    path = _folder(form_id) / "form.json"
    if not path.exists():
        raise FormNotFound(form_id)
    return json.loads(path.read_text())


def original_pdf(form_id: str) -> bytes:
    path = _folder(form_id) / "original.pdf"
    if not path.exists():
        raise FormNotFound(form_id)
    return path.read_bytes()


def save(form: dict, pdf: bytes | None = None) -> dict:
    folder = _folder(form["id"])
    folder.mkdir(parents=True, exist_ok=True)
    if pdf is not None:
        (folder / "original.pdf").write_bytes(pdf)
    form.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    form["updated_at"] = datetime.now(timezone.utc).isoformat()
    (folder / "form.json").write_text(json.dumps(form, ensure_ascii=False, indent=2))
    return form


def patient_view(form: dict) -> dict:
    """What the patient's phone needs: no clinic email, no internal bookkeeping."""
    keep = ("id", "clinic_name", "form_title_en", "form_title_ne", "questions", "consent")
    return {k: form.get(k) for k in keep}
