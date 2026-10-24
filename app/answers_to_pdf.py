"""Turn the patient's answers (by question) into PDF values (by field name)."""
from __future__ import annotations

import datetime as dt
import re

from .filler import SKIPPED_TEXT
from .nepali_dates import ASCII_DIGITS, format_for_form

SKIP = "__skip__"
TEXT_KINDS = {"text", "name", "number", "code", "email", "date"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


class BadAnswer(ValueError):
    pass


def build_values(form: dict, answers: dict, signer_name: str, today: dt.date | None = None):
    """Return (values, signature, skipped) for filler.fill_pdf.

    answers: {question_id: value | "__skip__"}; multi answers are lists of chosen option values.
    skipped: English question texts the patient left for the front desk.
    """
    today = today or dt.date.today()
    values, skipped, signature = {}, [], None
    for q in form["questions"]:
        kind, fields, qid = q["kind"], q["fields"], q["id"]
        if kind == "signature":
            signature = {"field": fields[0], "name": signer_name}
            continue
        if kind == "auto_date":
            values[fields[0]] = format_for_form(today, q.get("format", "MM/DD/YYYY"))
            continue
        if kind == "auto_name":
            values[fields[0]] = signer_name
            continue
        if kind == "skip":
            continue

        answer = answers.get(qid)
        if answer is None:
            continue                     # never reached; leave the box as the clinic sent it
        if answer == SKIP:
            skipped.append(q["en"])
            if kind in TEXT_KINDS:
                values[fields[0]] = SKIPPED_TEXT
            continue

        if kind in TEXT_KINDS:
            text = str(answer).translate(ASCII_DIGITS).strip()
            if DEVANAGARI.search(text):
                # the clinic's PDF font can't show Devanagari, and the clinic needs English
                raise BadAnswer(f"{qid}: answer must be in English letters")
            values[fields[0]] = text
        elif kind in ("yesno", "choice", "scale"):
            allowed = {o["value"] for o in q.get("options", [])}
            if str(answer) not in allowed:
                raise BadAnswer(f"{qid}: {answer!r} is not one of the options")
            values[fields[0]] = str(answer)
        elif kind == "multi":
            chosen = set(answer if isinstance(answer, list) else [])
            for f in fields:
                values[f] = f in chosen
    return values, signature, skipped
