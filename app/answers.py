"""Answer Interpreter: a patient's Nepali answer to one question -> the English for the form.

Gemini cleans up the speech-recognition text using the question as context and
writes the English. Plain code does the parts that must be exact: date
arithmetic, digit handling and phone formatting.
"""
from __future__ import annotations

import datetime as dt
import re

from . import gemini, nepali_dates

INTERPRETED_KINDS = {"text", "name", "number", "code", "email", "date"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")

SYSTEM = """You help an older Nepali-speaking patient fill in a United States clinic's English intake form.
You get one question from the form and the patient's answer. The answer came from speech recognition, or the
patient typed it, so it may contain recognition mistakes, Nepali number words or a mix of Nepali and English.

Rules:
- Only use what the patient said. Never invent, guess or add information, and never give medical advice.
- said_ne: the patient's answer as clean, correctly spelled Nepali (Devanagari). Fix obvious recognition errors
  using the question as context; keep their meaning and their words.
- en: what should be written in the form's box, in plain English, as the patient would write it.
- If the answer is unintelligible, empty, or doesn't answer this question at all, set ok to false.
"""

KIND_RULES = {
    "text": "Write a short, clear English answer in the first person, keeping every detail they gave "
            "(places, times, body parts, causes). Medicine names use their standard English spelling, with dose "
            "and frequency if given (e.g. 'Amlodipine 5 mg once a day').",
    "name": "This is a person's name. Spell it in English letters the way Nepali names are usually written in "
            "the US, in Title Case (न्यौपाने -> Neupane, श्रेष्ठ -> Shrestha, कमला -> Kamala). No titles like 'Mr'.",
    "number": "This is a number such as a phone number or ZIP code. Write only the digits they said, in order, "
              "converting Nepali digits or number words (एक दुई तीन...) to 0-9. No words.",
    "code": "This is an ID or claim number. Write the letters and digits exactly as said, in upper case, with no "
            "spaces. Nepali letter names for English letters (e.g. 'ए', 'बी', 'एक्स') mean those Latin letters.",
    "email": "This is an email address. Spoken 'at', 'at the rate' or 'एट' mean @; 'dot' or 'डट' mean '.'. "
             "Write it in lower case.",
    "date": "This is a date. Fill calendar, year, month and day. Use calendar BS if they used a Nepali month "
            "name (बैशाख, जेठ, असार, साउन, भदौ, असोज, कात्तिक, मंसिर, पुस, माघ, फागुन, चैत) or a Bikram "
            "Sambat year (roughly 1990-2090); use AD for English month names or AD years. month is 1-12 in that "
            "calendar. For a relative date ('three weeks ago', 'गएको मंगलबार'), work it out from today. Set "
            "en to the date in words.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "said_ne": {"type": "string"},
        "en": {"type": "string"},
        "calendar": {"type": "string", "enum": ["BS", "AD"]},
        "year": {"type": "integer"},
        "month": {"type": "integer"},
        "day": {"type": "integer"},
    },
    "required": ["ok", "said_ne", "en"],
}


class NotInterpretable(ValueError):
    pass


def _prompt(question: dict, transcript: str, today: dt.date) -> str:
    by, bm, bd = nepali_dates.ad_to_bs(today)
    return (
        f"Form question (English): {question['en']}\n"
        f"Question as asked in Nepali: {question['ne']}\n"
        f"Form section: {question.get('section_en', '')}\n"
        f"Answer type: {question['kind']}. {KIND_RULES[question['kind']]}\n"
        f"Today is {today.isoformat()} (AD), which is {by}-{bm:02d}-{bd:02d} in Bikram Sambat.\n"
        f"Patient's answer: {transcript}"
    )


def _format_phone(digits: str) -> str:
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return digits


def interpret(question: dict, transcript: str, today: dt.date | None = None) -> dict:
    """Return {"ok", "said", "en", "value", "parts"?}. "value" is what goes in the PDF box."""
    kind = question["kind"]
    if kind not in INTERPRETED_KINDS:
        raise NotInterpretable(kind)
    transcript = " ".join(str(transcript).split())
    if not transcript:
        return {"ok": False}
    today = today or dt.date.today()
    data = gemini.generate_json(_prompt(question, transcript, today), SCHEMA, system=SYSTEM)
    if not data.get("ok"):
        return {"ok": False}
    said = (data.get("said_ne") or transcript).strip()
    en = (data.get("en") or "").strip()

    if kind == "date":
        try:
            date = nepali_dates.to_date(data.get("calendar") or "AD", int(data["year"]), int(data["month"]),
                                        int(data["day"]))
        except (KeyError, TypeError, ValueError):
            return {"ok": False}
        value = nepali_dates.format_for_form(date, question.get("format", "MM/DD/YYYY"))
        calendar = (data.get("calendar") or "AD").upper()
        y, m, d = nepali_dates.ad_to_bs(date) if calendar == "BS" else (date.year, date.month, date.day)
        return {"ok": True, "said": nepali_dates.describe_ne(date, calendar),
                "en": f"{value} ({nepali_dates.describe_en(date)})", "value": value,
                "parts": {"calendar": calendar, "year": y, "month": m, "day": d}}

    en = en.translate(nepali_dates.ASCII_DIGITS)
    if kind == "number":
        digits = re.sub(r"\D", "", en)
        if len(digits) < 3:
            return {"ok": False}
        is_phone = "phone" in question["en"].lower() or "फोन" in question["ne"]
        en = _format_phone(digits) if is_phone else digits
    elif kind == "code":
        en = re.sub(r"\s+", "", en).upper()
    elif kind == "email":
        en = en.replace(" ", "").lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", en):
            return {"ok": False}
    if not en or DEVANAGARI.search(en):
        return {"ok": False}
    return {"ok": True, "said": said, "en": en, "value": en}
