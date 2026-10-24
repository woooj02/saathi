"""Mailer: the filled form goes to the clinic by email.

MAIL_MODE=file (the default) writes each email as an .eml file in data/outbox/,
which any mail program can open. Real sending is added in slice 6.
"""
from __future__ import annotations

import re
from datetime import datetime
from email.message import EmailMessage

from . import settings


def build_email(form: dict, pdf: bytes, patient_name: str, skipped: list[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg["To"] = form["clinic_email"]
    msg["Subject"] = f"Intake form: {patient_name}"
    lines = [
        f"{patient_name} completed {form.get('form_title_en') or 'your intake form'} with Saathi.",
        "They answered in Nepali; every answer on the attached form is in English.",
        "",
    ]
    if skipped:
        lines.append("Left for the front desk (marked \"Patient will provide at visit\" or left blank):")
        lines += [f"  - {s}" for s in skipped]
    else:
        lines.append("Every question was answered.")
    lines += ["", "Sent by Saathi for " + form["clinic_name"] + "."]
    msg.set_content("\n".join(lines))
    safe = re.sub(r"[^A-Za-z0-9]+", "-", patient_name).strip("-") or "patient"
    msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"intake-{safe}.pdf")
    return msg


def deliver(form: dict, pdf: bytes, patient_name: str, skipped: list[str]) -> str:
    """Returns the mail status: "saved" (file mode)."""
    msg = build_email(form, pdf, patient_name, skipped)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = settings.OUTBOX_DIR / f"{stamp}-{form['id']}.eml"
    path.write_bytes(bytes(msg))
    return "saved"
