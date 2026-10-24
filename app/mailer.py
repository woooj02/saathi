"""Mailer: the filled form goes to the clinic by email.

MAIL_MODE=file (the default) writes each email as an .eml file in data/outbox/,
which any mail program can open. MAIL_MODE=send sends it through SMTP (Zoho for
Keepsrunning), but never sooner than MIN_SEND_GAP_SECONDS after the last real
send: those sends are precious. An email that isn't sent is kept in the outbox,
and the patient still gets their copy.
"""
from __future__ import annotations

import logging
import re
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

from . import settings

log = logging.getLogger("saathi.mailer")
LAST_SEND = "last-send.txt"


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


def _keep(form: dict, msg: EmailMessage, why: str):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = settings.OUTBOX_DIR / f"{stamp}-{form['id']}{'' if why == 'saved' else '-' + why}.eml"
    path.write_bytes(bytes(msg))
    return path


def seconds_until_next_send() -> float:
    path = settings.OUTBOX_DIR / LAST_SEND
    if not path.exists():
        return 0.0
    try:
        last = float(path.read_text().strip())
    except ValueError:
        return 0.0
    return max(0.0, settings.MIN_SEND_GAP_SECONDS - (time.time() - last))


def deliver(form: dict, pdf: bytes, patient_name: str, skipped: list[str]) -> str:
    """Returns the mail status:
    "saved" (file mode), "sent", "deferred" (too soon after the last send) or "failed".
    """
    msg = build_email(form, pdf, patient_name, skipped)
    if settings.MAIL_MODE != "send":
        _keep(form, msg, "saved")
        return "saved"
    if not (settings.SMTP_USER and settings.SMTP_PASSWORD):
        log.warning("MAIL_MODE=send but SMTP_USER/SMTP_PASSWORD are missing; keeping the email in the outbox")
        _keep(form, msg, "failed")
        return "failed"
    wait = seconds_until_next_send()
    if wait > 0:
        log.info("holding the email: next real send allowed in %.0f s", wait)
        _keep(form, msg, "deferred")
        return "deferred"
    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        log.warning("sending failed: %s", exc)
        _keep(form, msg, "failed")
        return "failed"
    (settings.OUTBOX_DIR / LAST_SEND).write_text(str(time.time()))
    log.info("sent the intake form for %s to %s", patient_name, msg["To"])
    return "sent"
