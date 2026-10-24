"""PDF Filler: write English answers and a typed signature into the clinic's own PDF.

Values are keyed by the PDF's field names:
- text fields take a string
- checkboxes take True/False
- radio groups take the export value of the chosen button (e.g. "Yes", "7")

The signature is drawn in a handwriting font where the signature box was, the way
e-signature tools show a typed name. The empty box is removed first, because form
boxes are painted on top of the page and would hide the drawing.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

FONT_DIR = Path(__file__).resolve().parent.parent / "web" / "fonts"
SIGNATURE_FONT = FONT_DIR / "DancingScript.ttf"
SKIPPED_TEXT = "Patient will provide at visit"


def _fit_size(text: str, font: pymupdf.Font, width: float, height: float, start: float) -> float:
    size = start
    while size > 6 and (font.text_length(text, fontsize=size) > width - 6 or size > height * 0.9):
        size -= 0.5
    return size


def draw_signature(page, rect: pymupdf.Rect, name: str):
    page.draw_line(pymupdf.Point(rect.x0, rect.y1), pymupdf.Point(rect.x1, rect.y1), width=0.6)
    font = pymupdf.Font(fontfile=str(SIGNATURE_FONT))
    size = _fit_size(name, font, rect.width, rect.height + 10, 22)
    page.insert_font(fontname="sig", fontfile=str(SIGNATURE_FONT))
    baseline = pymupdf.Point(rect.x0 + 4, rect.y1 - rect.height * 0.22)
    page.insert_text(baseline, name, fontname="sig", fontsize=size, color=(0.05, 0.05, 0.25))


def _fit_text(w) -> None:
    """Shrink the font of a one-line box so the whole answer shows (e.g. the skip note in a narrow box)."""
    if w.field_flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE or not w.field_value:
        return
    size = w.text_fontsize or 10
    room = w.rect.width - 4
    while size > 6 and pymupdf.get_text_length(w.field_value, fontname="helv", fontsize=size) > room:
        size -= 0.5
    w.text_fontsize = size


def fill_pdf(original: bytes, values: dict, signature: dict | None = None) -> bytes:
    """Return a filled copy of `original`.

    signature = {"field": <signature field name>, "name": <typed full name>}
    """
    doc = pymupdf.open(stream=original, filetype="pdf")
    sig_field = (signature or {}).get("field")
    for page in doc:
        for w in list(page.widgets()):
            name = w.field_name
            if name == sig_field:
                rect = pymupdf.Rect(w.rect)
                page.delete_widget(w)
                draw_signature(page, rect, signature["name"])
                continue
            if name not in values:
                continue
            value = values[name]
            if w.field_type == pymupdf.PDF_WIDGET_TYPE_TEXT:
                w.field_value = "" if value is None else str(value)
                _fit_text(w)
                w.update()
            elif w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                w.field_value = w.on_state() if value else "Off"
                w.update()
            elif w.field_type == pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON:
                if value is not None and w.on_state() == str(value):
                    w.field_value = w.on_state()
                    w.update()
            elif w.field_type in (pymupdf.PDF_WIDGET_TYPE_COMBOBOX, pymupdf.PDF_WIDGET_TYPE_LISTBOX):
                w.field_value = str(value)
                w.update()
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out


def read_values(pdf: bytes) -> dict:
    """What a PDF viewer would show in each field (used by tests and the filled-PDF check)."""
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    out = {}
    for page in doc:
        for w in page.widgets():
            if w.field_type == pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON:
                if w.field_value not in ("Off", "", None, False):
                    out[w.field_name] = w.on_state()
                else:
                    out.setdefault(w.field_name, None)
            elif w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                out[w.field_name] = w.field_value not in ("Off", "", None, False)
            else:
                out[w.field_name] = w.field_value
    doc.close()
    return out
