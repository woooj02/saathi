import datetime as dt
import email
from email import policy

import pytest
from fastapi.testclient import TestClient

from app import nepali_dates, settings
from app.filler import SKIPPED_TEXT, read_values
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("bs,ad", [
    ((2081, 4, 15), dt.date(2024, 7, 30)),     # Shrawan 15, 2081
    ((2082, 1, 1), dt.date(2025, 4, 14)),      # Nepali new year 2082
    ((2021, 9, 30), dt.date(1965, 1, 13)),
])
def test_bs_to_ad_known_pairs(bs, ad):
    assert nepali_dates.bs_to_ad(*bs) == ad
    assert nepali_dates.ad_to_bs(ad) == bs


def test_bad_bs_day_is_rejected():
    with pytest.raises(nepali_dates.BadDate):
        nepali_dates.bs_to_ad(2081, 1, 32)   # Baisakh 2081 has 31 days


def test_date_endpoint_formats_for_the_form():
    r = client.get("/api/dates/convert", params={"calendar": "BS", "year": 2081, "month": 4, "day": 15})
    assert r.json() == {"value": "07/30/2024", "en": "July 30, 2024", "ne": "२०८१ साउन १५"}


def test_patient_view_hides_clinic_email():
    form = client.get("/api/forms/sample").json()
    assert form["clinic_name"] == "Riverbend Physical Therapy"
    assert "clinic_email" not in form
    assert client.get("/api/forms/doesnotexist").status_code == 404


ANSWERS = {
    "last_name": "Neupane", "first_name": "Kamala", "date_of_birth": "01/13/1965", "sex": "Female",
    "phone": "३०३५५५०१४२", "needs_interpreter": "Yes", "pain_areas": ["pain_lower_back", "pain_hip"],
    "pain_now": "7", "insurance_member_id": "__skip__", "seen_er": "__skip__",
    "injury_description": "I slipped on ice in the parking lot at work.",
}


def test_submit_fills_the_pdf_and_writes_the_email():
    before = set(settings.OUTBOX_DIR.glob("*.eml"))
    r = client.post("/api/forms/sample/submit", json={"answers": ANSWERS, "signer_name": "Kamala  Neupane"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["x-mail-status"] == "saved"
    values = read_values(r.content)
    assert values["last_name"] == "Neupane"
    assert values["phone"] == "3035550142"            # Nepali digits become ASCII
    assert values["pain_hip"] is True and values["pain_neck"] is False
    assert values["pain_now"] == "7"
    assert values["insurance_member_id"] == SKIPPED_TEXT
    assert values["seen_er"] is None                  # a skipped radio stays empty
    assert values["printed_name"] == "Kamala Neupane"
    assert values["signature_date"] == dt.date.today().strftime("%m/%d/%Y")

    new = set(settings.OUTBOX_DIR.glob("*.eml")) - before
    assert len(new) == 1
    msg = email.message_from_bytes(new.pop().read_bytes(), policy=policy.default)
    assert msg["Subject"] == "Intake form: Kamala Neupane"
    body = msg.get_body(("plain",)).get_content()
    assert "Member ID" in body and "emergency room" in body   # skipped questions are listed
    assert [p.get_filename() for p in msg.iter_attachments()] == ["intake-Kamala-Neupane.pdf"]


def test_devanagari_answers_are_refused_without_translation():
    r = client.post("/api/forms/sample/submit", json={"answers": {"last_name": "न्यौपाने"}, "signer_name": "Kamala"})
    assert r.status_code == 422
    r = client.post("/api/forms/sample/submit", json={"answers": {}, "signer_name": "कमला"})
    assert r.status_code == 422


def test_options_must_be_real():
    r = client.post("/api/forms/sample/submit", json={"answers": {"pain_now": "11"}, "signer_name": "Kamala"})
    assert r.status_code == 422
