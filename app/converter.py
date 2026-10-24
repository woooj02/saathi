"""Form Converter: the reader's list of boxes -> plain questions in English and Nepali (Gemini).

One Gemini call per uploaded form. Code then checks the result against the PDF
itself, because the PDF is the source of truth:
- every fillable box is covered by exactly one question (a missing box gets a
  second, smaller call, then a plain fallback the clinic can reword)
- option values are the PDF's real export values, so filling can't drift
- question ids are unique
"""
from __future__ import annotations

import json
import logging
import re

from . import gemini

log = logging.getLogger("saathi.converter")

KINDS = ["text", "name", "date", "number", "code", "email", "yesno", "choice", "multi", "scale",
         "signature", "auto_date", "auto_name", "skip"]

SYSTEM = """You turn a US clinic's English PDF intake form into questions an older Nepali-speaking patient can
answer alone on a phone, one question per screen. The patient may have little schooling, so the Nepali must be
plain, warm, everyday Nepali (address the patient as तपाईं), not literal or bureaucratic translation. Explain
US-specific terms briefly in Nepali where needed (e.g. ZIP code, Member ID, workers' compensation).

You get the form's fillable boxes (with the printed label next to each box) and its long paragraphs.

For questions:
- Cover every box exactly once, using the box names given, in the order they appear on the form.
- One text/date/number box = one question. A radio group = one question (kind yesno if its options are just
  Yes/No, kind scale if it's a 0-10 rating, otherwise choice), and its options must use the radio group's exact
  option values. A run of checkboxes under one prompt = one question of kind multi whose fields are those
  checkbox names and whose option values are the checkbox names.
- kinds: name (person names), date, number (phone, ZIP, other numbers), code (IDs, claim and group numbers),
  email, text (everything else typed), yesno, choice, multi, scale.
- The patient's signature box: kind signature. The date next to the signature: kind auto_date. A "printed name"
  box next to the signature: kind auto_name. Boxes only for someone else signing on the patient's behalf, or for
  office use only: kind skip.
- en: the question in plain English, as a full question. ne: the same question in plain Nepali.
- section_en/section_ne: the form section it's in, short.
- help_ne (optional): one short Nepali hint, only where it truly helps (e.g. where to find a number).
- optional: true if the form says "if any" / "if applicable" or most patients won't have it.
- long: true for boxes expecting a few sentences.
- format: for dates, the format printed on the form, else MM/DD/YYYY.
- suggestions (optional, text questions only): a few common answers to tap, each {en, ne}.

For consent: each paragraph the patient is agreeing to or acknowledging (treatment consent, privacy/HIPAA,
financial responsibility, cancellation, release of information), as {id, title_en, title_ne, en, ne} where en is
the original text unchanged and ne is a faithful plain-Nepali explanation of the same content: don't add,
soften or drop any obligation. Leave out instructions like "please fill in every page".
"""

OPTION = {"type": "object", "properties": {"value": {"type": "string"}, "en": {"type": "string"},
                                           "ne": {"type": "string"}}, "required": ["value", "en", "ne"]}
QUESTION = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string", "enum": KINDS},
        "fields": {"type": "array", "items": {"type": "string"}},
        "en": {"type": "string"},
        "ne": {"type": "string"},
        "section_en": {"type": "string"},
        "section_ne": {"type": "string"},
        "help_ne": {"type": "string"},
        "optional": {"type": "boolean"},
        "long": {"type": "boolean"},
        "format": {"type": "string"},
        "options": {"type": "array", "items": OPTION},
        "suggestions": {"type": "array", "items": {"type": "object", "properties": {
            "en": {"type": "string"}, "ne": {"type": "string"}}, "required": ["en", "ne"]}},
    },
    "required": ["id", "kind", "fields", "en", "ne", "section_en", "section_ne"],
}
SCHEMA = {
    "type": "object",
    "properties": {
        "form_title_en": {"type": "string"},
        "form_title_ne": {"type": "string"},
        "questions": {"type": "array", "items": QUESTION},
        "consent": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "title_en": {"type": "string"}, "title_ne": {"type": "string"},
            "en": {"type": "string"}, "ne": {"type": "string"}},
            "required": ["id", "title_en", "title_ne", "en", "ne"]}},
    },
    "required": ["form_title_en", "form_title_ne", "questions", "consent"],
}


def _describe(fields: list[dict]) -> list[dict]:
    """The reader's output, trimmed to what Gemini needs (no rectangles)."""
    out = []
    for f in fields:
        item = {"name": f["name"], "type": f["kind"], "page": f["page"], "label": f["label"], "section": f["section"]}
        if f.get("prompt") and f["prompt"] != f["label"]:
            item["prompt"] = f["prompt"]
        if f.get("options"):
            item["options"] = f["options"]
        if f.get("multiline"):
            item["multiline"] = True
        if f.get("hint"):
            item["hint"] = f["hint"]
        out.append(item)
    return out


def _prompt(read: dict, only: list[str] | None = None) -> str:
    fields = read["fields"] if only is None else [f for f in read["fields"] if f["name"] in only]
    parts = [f"The form has {read['pages']} pages.",
             "Fillable boxes, in order:", json.dumps(_describe(fields), ensure_ascii=False)]
    if only is None:
        parts += ["Long paragraphs on the form:", json.dumps(read["paragraphs"], ensure_ascii=False)]
    else:
        parts.append("Write questions for exactly these boxes. Return an empty consent list.")
    return "\n".join(parts)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "q"


def _fallback(field: dict) -> dict:
    """A plain question built from the PDF alone, for a box Gemini left out. The clinic can reword it."""
    label = field["label"] or field["prompt"] or field["name"]
    kind = {"checkbox": "multi", "signature": "signature"}.get(field["kind"], "text")
    q = {"id": field["name"], "kind": kind, "fields": [field["name"]], "en": label, "ne": label,
         "section_en": field["section"].title(), "section_ne": field["section"].title(), "needs_review": True}
    if field["kind"] == "radio":
        values = [o["value"] for o in field["options"]]
        q["kind"] = "yesno" if sorted(values) == ["No", "Yes"] else "choice"
        q["options"] = [{"value": o["value"], "en": o["label"] or o["value"], "ne": o["label"] or o["value"]}
                        for o in field["options"]]
    if kind == "multi":
        q["options"] = [{"value": field["name"], "en": label, "ne": label}]
    if field.get("hint") == "date":
        q["kind"], q["format"] = "date", "MM/DD/YYYY"
    return q


def _clean(questions: list[dict], read: dict) -> list[dict]:
    """Keep the AI's wording, but make the structure agree with the PDF."""
    by_name = {f["name"]: f for f in read["fields"]}
    seen_fields, seen_ids, out = set(), set(), []
    for q in questions:
        fields = [f for f in q.get("fields", []) if f in by_name and f not in seen_fields]
        if not fields or q.get("kind") not in KINDS:
            continue
        q["fields"] = fields
        first = by_name[fields[0]]
        if first["kind"] == "radio":
            real = [o["value"] for o in first["options"]]
            given = {o.get("value"): o for o in q.get("options", [])}
            if set(given) != set(real):
                # rebuild from the PDF; reuse the AI's wording by position when the counts match
                ai_opts = q.get("options", [])
                q["options"] = [{"value": v, "en": (ai_opts[i]["en"] if len(ai_opts) == len(real) else o["label"] or v),
                                 "ne": (ai_opts[i]["ne"] if len(ai_opts) == len(real) else o["label"] or v)}
                                for i, (v, o) in enumerate(zip(real, first["options"]))]
            else:
                q["options"] = [given[v] for v in real]
            if q["kind"] not in ("yesno", "choice", "scale"):
                q["kind"] = "yesno" if sorted(real) == ["No", "Yes"] else "choice"
            q["fields"] = fields[:1]
        elif q["kind"] == "multi":
            names = {o.get("value") for o in q.get("options", [])}
            if names != set(fields):
                q["options"] = [{"value": f, "en": by_name[f]["label"], "ne": by_name[f]["label"]} for f in fields]
        elif q["kind"] in ("yesno", "choice", "scale"):
            q["kind"] = "text"            # a choice question on a text box: just ask for text
            q.pop("options", None)
        else:
            q["fields"] = fields[:1]
        base = _slug(q.get("id") or fields[0])
        qid, n = base, 2
        while qid in seen_ids:
            qid, n = f"{base}_{n}", n + 1
        q["id"] = qid
        seen_ids.add(qid)
        seen_fields.update(q["fields"])
        out.append(q)
    return out


def _covered(questions):
    return {f for q in questions for f in q["fields"]}


def convert(read: dict) -> dict:
    """Return {"form_title_en", "form_title_ne", "questions", "consent", "needs_review": [field names]}."""
    data = gemini.generate_json(_prompt(read), SCHEMA, system=SYSTEM, think=True)
    questions = _clean(data.get("questions", []), read)
    order = [f["name"] for f in read["fields"]]
    missing = [n for n in order if n not in _covered(questions)]
    if missing:
        log.info("conversion missed %d boxes; asking again for those", len(missing))
        try:
            extra = gemini.generate_json(_prompt(read, only=missing), SCHEMA, system=SYSTEM)
            questions += _clean(extra.get("questions", []), {"fields": [f for f in read["fields"] if f["name"] in missing]})
        except gemini.AIError:
            pass
    by_name = {f["name"]: f for f in read["fields"]}
    still = [n for n in order if n not in _covered(questions)]
    questions += [_fallback(by_name[n]) for n in still]
    # keep the form's own order: by the position of each question's first box
    position = {n: i for i, n in enumerate(order)}
    questions.sort(key=lambda q: position[q["fields"][0]])
    questions = _clean(questions, read)   # again, for unique ids across the merged list
    return {
        "form_title_en": data.get("form_title_en") or "Intake form",
        "form_title_ne": data.get("form_title_ne") or "फारम",
        "questions": questions,
        "consent": [c for c in data.get("consent", []) if c.get("en") and c.get("ne")],
        "needs_review": still,
    }
