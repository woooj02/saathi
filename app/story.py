"""Story: the patient tells their story once, in their own words, and Saathi fills every box it heard.

One Gemini call listens to the whole recording with the form's questions as context and
returns an answer only for what the patient clearly said. Each answer then goes through
the same checks as a single spoken answer (answers._finish for typed ones, the PDF's own
option values for taps), so a story can't put anything on the form a question couldn't.
"""
from __future__ import annotations

import datetime as dt

from . import answers, gemini, nepali_dates

TAP_KINDS = {"yesno", "choice", "scale"}
STORY_KINDS = answers.INTERPRETED_KINDS | TAP_KINDS | {"multi"}

SYSTEM = """You help an older Nepali-speaking patient fill in a United States clinic's English intake form.
Instead of answering questions one by one, the patient has told their story in their own words, in a recording
(Nepali, possibly mixed with English). You get the form's questions and the recording.

Rules:
- Answer a question only if the patient clearly said the answer. Never guess, infer or fill a typical value; leave
  out every question they didn't answer. A short, correct list is far better than a long, guessed one.
- Never give medical advice. Don't add details they didn't say.
- story_ne: everything the patient said, as clean, correctly spelled Nepali (Devanagari).
- For each answer, said_ne is the patient's own words for that part, in Nepali, and the other fields follow the
  question's answer type (given in the question list).
"""

TAP_RULE = "Pick value from the listed option values, only if what they said clearly matches one."
MULTI_RULE = "List every option value they clearly mentioned (e.g. each body part that hurts)."


def _question_lines(questions: list[dict]) -> str:
    lines = []
    for q in questions:
        line = f"- id {q['id']} ({q['kind']}): {q['en']} / {q['ne']}"
        if q["kind"] in answers.KIND_RULES:
            line += f"\n  Answer type: {answers.KIND_RULES[q['kind']]}"
        if q["kind"] in TAP_KINDS | {"multi"}:
            opts = ", ".join(f"{o['value']} = {o['en']}" for o in q.get("options", []))
            line += f"\n  {MULTI_RULE if q['kind'] == 'multi' else TAP_RULE} Options: {opts}"
        lines.append(line)
    return "\n".join(lines)


def _answer_schema(q: dict) -> dict:
    props = {"said_ne": {"type": "string"}}
    if q["kind"] == "date":
        props.update(calendar={"type": "string", "enum": ["BS", "AD"]}, year={"type": "integer"},
                     month={"type": "integer"}, day={"type": "integer"}, en={"type": "string"})
    elif q["kind"] in TAP_KINDS:
        props["value"] = {"type": "string", "enum": [o["value"] for o in q.get("options", [])]}
    elif q["kind"] == "multi":
        props["values"] = {"type": "array", "items": {"type": "string", "enum": [o["value"] for o in q.get("options", [])]}}
    else:
        props["en"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": ["said_ne"]}


def _schema(questions: list[dict]) -> dict:
    return {
        "type": "object",
        "properties": {
            "story_ne": {"type": "string"},
            "answers": {"type": "object", "properties": {q["id"]: _answer_schema(q) for q in questions}},
        },
        "required": ["story_ne", "answers"],
    }


def _check(q: dict, a: dict) -> dict | None:
    """One answer from the story -> the same record a single answer makes, or None if it doesn't hold up."""
    said = (a.get("said_ne") or "").strip()
    if q["kind"] in TAP_KINDS:
        opt = next((o for o in q.get("options", []) if o["value"] == a.get("value")), None)
        return opt and {"value": opt["value"], "said": said or opt["ne"], "en": opt["en"]}
    if q["kind"] == "multi":
        chosen = [o for o in q.get("options", []) if o["value"] in (a.get("values") or [])]
        return chosen and {"value": [o["value"] for o in chosen], "said": said or ", ".join(o["ne"] for o in chosen),
                           "en": ", ".join(o["en"] for o in chosen)}
    rec = answers._finish(q, {"ok": True, **a}, said)
    return rec if rec.get("ok") else None


def extract(form: dict, audio: bytes, mime: str, today: dt.date | None = None) -> dict:
    """Return {"said": the story in Nepali, "answers": {question_id: {value, said, en, parts?}}}."""
    today = today or dt.date.today()
    questions = [q for q in form["questions"] if q["kind"] in STORY_KINDS]
    by, bm, bd = nepali_dates.ad_to_bs(today)
    prompt = (f"Today is {today.isoformat()} (AD), which is {by}-{bm:02d}-{bd:02d} in Bikram Sambat.\n"
              f"The form's questions:\n{_question_lines(questions)}\n\n"
              "The patient's story is the attached audio recording.")
    data = gemini.generate_json(prompt, _schema(questions), system=SYSTEM, audio=(audio, mime), think=True)
    by_id = {q["id"]: q for q in questions}
    found = {}
    for qid, a in (data.get("answers") or {}).items():
        if qid in by_id and isinstance(a, dict):
            rec = _check(by_id[qid], a)
            if rec:
                rec.pop("ok", None)
                found[qid] = {**rec, "story": True}
    return {"said": (data.get("story_ne") or "").strip(), "answers": found}
