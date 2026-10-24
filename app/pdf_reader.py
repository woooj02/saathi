"""Form Reader: list every fillable box in a PDF with the words printed next to it.

No AI here. PyMuPDF gives us each box (a "widget"): its type, its rectangle and its
internal field name. Internal names are often meaningless ("Text12"), so the label
comes from the printed page instead:

- text boxes: the words just above the box, or else to its left on the same row
- checkboxes and radio buttons: the words just to the right of each button
- a radio group or a block of checkboxes also gets a "prompt": the words to the left
  of its first button, or the nearest line above that isn't itself a row of boxes

The output is plain JSON-ready dicts, which is what the converter sends to Gemini.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

import pymupdf


class NotFillable(Exception):
    """The PDF has no fillable boxes."""


class NotAPdf(Exception):
    """The bytes couldn't be opened as a PDF."""


KIND_BY_TYPE = {
    pymupdf.PDF_WIDGET_TYPE_TEXT: "text",
    pymupdf.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
    pymupdf.PDF_WIDGET_TYPE_COMBOBOX: "choice",
    pymupdf.PDF_WIDGET_TYPE_LISTBOX: "choice",
    pymupdf.PDF_WIDGET_TYPE_SIGNATURE: "signature",
}

PARAGRAPH_MIN_WORDS = 25


@dataclass
class Field:
    name: str
    kind: str                      # text | checkbox | radio | choice | signature
    page: int                      # 1-based
    rect: list[float]
    label: str = ""
    prompt: str = ""               # the question a radio group / checkbox block sits under
    section: str = ""
    options: list[dict] = field(default_factory=list)   # radio/choice: [{value, label}]
    multiline: bool = False
    hint: str = ""                 # "date" | "signature" | ""


@dataclass
class Line:
    text: str
    rect: pymupdf.Rect
    size: float
    bold: bool


def _lines(page) -> list[Line]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = " ".join(s["text"].strip() for s in spans)
            bold = all("Bold" in s["font"] or s["flags"] & 16 for s in spans)
            out.append(Line(text, pymupdf.Rect(line["bbox"]), max(s["size"] for s in spans), bold))
    return out


def _join(words) -> str:
    return " ".join(w[4] for w in sorted(words, key=lambda w: (round(w[1]), w[0]))).strip()


def _words_above(words, r: pymupdf.Rect, reach=16) -> str:
    hits = [w for w in words if r.y0 - reach <= w[3] <= r.y0 + 1 and r.x0 - 2 <= w[0] < r.x1]
    if not hits:
        return ""
    # keep only the closest printed line above the box
    bottom = max(w[3] for w in hits)
    return _join([w for w in hits if abs(w[3] - bottom) < 3])


def _words_left(words, r: pymupdf.Rect, stop_x=0.0) -> str:
    cy = (r.y0 + r.y1) / 2
    row = [w for w in words if w[1] - 2 <= cy <= w[3] + 2 and stop_x <= w[0] and w[2] <= r.x0 + 1]
    return _join(row)


def _words_right(words, r: pymupdf.Rect, stop_x: float) -> str:
    """Consecutive words starting just right of a button, until a wide gap or the next button."""
    cy = (r.y0 + r.y1) / 2
    row = sorted((w for w in words if w[1] - 2 <= cy <= w[3] + 2 and w[0] >= r.x1 - 1 and w[2] <= stop_x + 1),
                 key=lambda w: w[0])
    picked, last_x = [], r.x1
    for w in row:
        if w[0] - last_x > 12:
            break
        picked.append(w)
        last_x = w[2]
    return " ".join(w[4] for w in picked)


def _row_has_boxes(line: Line, rects) -> bool:
    return any(rr.y0 - 3 <= (line.rect.y0 + line.rect.y1) / 2 <= rr.y1 + 3 for rr in rects)


def _is_box_label(line: Line, rects) -> bool:
    """A short line sitting right on top of a box is that box's label, not prose."""
    return any(0 <= rr.y0 - line.rect.y1 <= 16 and line.rect.x0 < rr.x1 and rr.x0 < line.rect.x1 for rr in rects)


def _prompt_above(lines: list[Line], r: pymupdf.Rect, rects, reach=90) -> str:
    """The nearest line above that isn't itself a row of boxes (the block's question)."""
    candidates = [ln for ln in lines if ln.rect.y1 <= r.y0 + 1 and r.y0 - ln.rect.y1 <= reach
                  and not _row_has_boxes(ln, rects) and not _is_heading(ln)]
    if not candidates:
        return ""
    return max(candidates, key=lambda ln: ln.rect.y1).text


HEADER_BAND = 0.08   # the top 8% of a page is letterhead, not section headings


def _is_heading(ln: Line, page_height: float = 0) -> bool:
    if page_height and ln.rect.y1 < page_height * HEADER_BAND:
        return False
    return ln.bold and (ln.size >= 10 or ln.text.isupper())


DATE_RE = re.compile(r"\bdate\b|mm/dd|d\.o\.b|\bdob\b", re.I)


def _hint(label: str, name: str) -> str:
    if DATE_RE.search(label) or (not label and DATE_RE.search(name)):
        return "date"
    if "signature" in f"{label} {name}".lower() and "relationship" not in label.lower():
        return "signature"
    return ""


def read_form(data: bytes) -> dict:
    """Return {"pages": n, "fields": [...], "paragraphs": [...]} for a fillable PDF."""
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several types for junk input
        raise NotAPdf(str(exc)) from exc
    if not doc.is_pdf:
        raise NotAPdf("not a PDF")

    fields: dict[str, Field] = {}
    paragraphs = []
    section = ""
    for pno, page in enumerate(doc, start=1):
        widgets = list(page.widgets())
        words = page.get_text("words")
        lines = _lines(page)
        rects = [w.rect for w in widgets]
        headings = sorted((ln for ln in lines if _is_heading(ln, page.rect.height)),
                          key=lambda ln: ln.rect.y0)

        def section_at(y):
            above = [h.text for h in headings if h.rect.y1 <= y and h.size < 14]
            return above[-1] if above else section

        for w in sorted(widgets, key=lambda w: (w.rect.y0, w.rect.x0)):
            kind = KIND_BY_TYPE.get(w.field_type)
            if not kind:
                continue
            r = w.rect
            # where does the next box on this row start? (stops a label running into it)
            right_stop = min([o.x0 for o in rects if o.x0 > r.x1 and abs(o.y0 - r.y0) < 4] or [page.rect.x1])

            if kind == "radio":
                f = fields.get(w.field_name)
                if f is None:
                    f = fields[w.field_name] = Field(
                        w.field_name, "radio", pno, list(r), section=section_at(r.y0),
                        prompt=_words_left(words, r) or _prompt_above(lines, r, rects))
                    f.label = f.prompt
                f.options.append({"value": w.on_state() or "", "label": _words_right(words, r, right_stop)})
                continue

            if kind == "checkbox":
                label = _words_right(words, r, right_stop) or _words_left(words, r)
                f = Field(w.field_name, "checkbox", pno, list(r), label=label, section=section_at(r.y0),
                          prompt=_prompt_above(lines, r, rects))
            elif kind == "choice":
                label = _words_above(words, r) or _words_left(words, r)
                f = Field(w.field_name, "choice", pno, list(r), label=label, section=section_at(r.y0),
                          options=[{"value": v, "label": v} for v in (w.choice_values or [])])
            else:
                label = _words_above(words, r) or _words_left(words, r) or (w.field_label or "")
                f = Field(w.field_name, kind, pno, list(r), label=label, section=section_at(r.y0),
                          multiline=bool(w.field_flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE))
            f.hint = "signature" if kind == "signature" else _hint(f.label, f.name)
            fields[w.field_name] = f

        # long printed paragraphs: consent, privacy, payment terms, instructions
        body = [ln for ln in lines if not _is_heading(ln) and ln.rect.y1 > page.rect.height * HEADER_BAND
                and not _row_has_boxes(ln, rects) and not _is_box_label(ln, rects)]
        run: list[Line] = []
        for ln in sorted(body, key=lambda ln: ln.rect.y0) + [None]:
            # consecutive lines with normal line spacing form one paragraph
            if ln is not None and run and ln.rect.y0 - run[-1].rect.y1 < ln.size * 0.9:
                run.append(ln)
                continue
            text = " ".join(x.text for x in run)
            if len(text.split()) >= PARAGRAPH_MIN_WORDS:
                paragraphs.append({"page": pno, "section": section_at(run[0].rect.y0), "text": text})
            run = [ln] if ln is not None else []

        if headings:
            section = [h.text for h in headings if h.size < 14][-1] if any(h.size < 14 for h in headings) else section

    if not fields:
        raise NotFillable("This PDF has no fillable boxes.")
    return {"pages": len(doc), "fields": [asdict(f) for f in fields.values()], "paragraphs": paragraphs}
