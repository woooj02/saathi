import pymupdf
import pytest

from app.filler import SKIPPED_TEXT, fill_pdf, read_values
from app.pdf_reader import NotAPdf, NotFillable, read_form


def by_name(form):
    return {f["name"]: f for f in form["fields"]}


def test_reader_finds_every_box(sample_pdf):
    form = read_form(sample_pdf)
    fields = by_name(form)
    assert form["pages"] == 5
    assert len(fields) == 70
    kinds = {f["kind"] for f in fields.values()}
    assert kinds == {"text", "radio", "checkbox"}


def test_labels_come_from_printed_text(sample_pdf):
    f = by_name(read_form(sample_pdf))
    assert f["last_name"]["label"] == "Last name"
    assert f["date_of_birth"]["label"] == "Date of birth (MM/DD/YYYY)"
    assert f["emergency_phone"]["label"] == "Phone number"
    assert f["pain_hip"]["label"] == "Hip"
    assert f["pain_hip"]["prompt"].startswith("Where is your pain?")
    assert f["hx_diabetes"]["prompt"].startswith("Do you have, or have you had")
    assert f["seen_er"]["prompt"] == "Did you go to an emergency room or urgent care?"
    assert f["emergency_name"]["section"] == "EMERGENCY CONTACT"


def test_radio_groups_keep_their_options(sample_pdf):
    f = by_name(read_form(sample_pdf))
    assert [o["value"] for o in f["pain_now"]["options"]] == [str(i) for i in range(11)]
    assert {"value": "Fall", "label": "Slip or fall"} in f["accident_type"]["options"]


def test_hints_and_paragraphs(sample_pdf):
    form = read_form(sample_pdf)
    f = by_name(form)
    assert f["patient_signature"]["hint"] == "signature"
    assert f["signature_date"]["hint"] == "date"
    assert f["injury_date"]["hint"] == "date"
    consent = [p for p in form["paragraphs"] if p["page"] == 5]
    assert len(consent) == 3
    assert consent[1]["section"].startswith("PRIVACY NOTICE")
    assert not any("Patient signature" in p["text"] for p in consent)


def test_flat_pdf_is_not_fillable():
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Name: ________")
    with pytest.raises(NotFillable):
        read_form(doc.tobytes())


def test_junk_is_not_a_pdf():
    with pytest.raises(NotAPdf):
        read_form(b"hello, this is not a pdf")


def test_filler_writes_values_back(sample_pdf):
    values = {
        "last_name": "Neupane", "sex": "Female", "pain_hip": True, "pain_neck": False,
        "pain_now": "7", "insurance_member_id": SKIPPED_TEXT, "injury_description": "Slipped on ice.",
    }
    out = read_values(fill_pdf(sample_pdf, values))
    for k, v in values.items():
        assert out[k] == v, k
    assert out["has_attorney"] is None   # untouched radio stays empty


def test_signature_is_drawn(sample_pdf):
    pdf = fill_pdf(sample_pdf, {}, {"field": "patient_signature", "name": "Kamala Neupane"})
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    assert "Kamala Neupane" in doc[4].get_text()
    assert "patient_signature" not in {w.field_name for w in doc[4].widgets()}
