import copy
import json

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import converter, gemini, settings
from app.main import app
from app.pdf_reader import read_form

client = TestClient(app)
SAMPLE = json.loads((settings.SAMPLES_DIR / "pt-intake" / "form.json").read_text())


def sample_reply():
    """A conversion like Gemini's, made from the hand-written sample."""
    return {"form_title_en": SAMPLE["form_title_en"], "form_title_ne": SAMPLE["form_title_ne"],
            "questions": copy.deepcopy(SAMPLE["questions"]), "consent": copy.deepcopy(SAMPLE["consent"])}


@pytest.fixture
def ai(monkeypatch):
    replies = []

    def fake(prompt, schema, **kw):
        return replies.pop(0)
    monkeypatch.setattr(gemini, "generate_json", fake)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    return replies


def test_convert_covers_every_box_once(sample_pdf, ai):
    ai.append(sample_reply())
    read = read_form(sample_pdf)
    out = converter.convert(read)
    covered = [f for q in out["questions"] for f in q["fields"]]
    assert sorted(covered) == sorted(f["name"] for f in read["fields"])
    assert out["needs_review"] == []
    assert len(out["consent"]) == 3


def test_missing_boxes_are_asked_again_then_fall_back(sample_pdf, ai):
    reply = sample_reply()
    reply["questions"] = [q for q in reply["questions"] if q["id"] not in ("phone", "seen_er", "pain_areas")]
    second = {"form_title_en": "", "form_title_ne": "", "consent": [],
              "questions": [q for q in SAMPLE["questions"] if q["id"] == "phone"]}
    ai.extend([reply, second])
    out = converter.convert(read_form(sample_pdf))
    by_field = {f: q for q in out["questions"] for f in q["fields"]}
    assert by_field["phone"]["ne"] == "तपाईंको फोन नम्बर के हो?"          # recovered by the second call
    assert by_field["seen_er"]["kind"] == "yesno"                           # plain fallback from the PDF
    assert by_field["seen_er"]["needs_review"] is True
    assert {o["value"] for o in by_field["seen_er"]["options"]} == {"Yes", "No"}
    assert set(out["needs_review"]) >= {"seen_er", "pain_head"}
    order = [q["fields"][0] for q in out["questions"]]
    assert order.index("phone") < order.index("seen_er") < order.index("pain_head")   # form order kept


def test_option_values_come_from_the_pdf(sample_pdf, ai):
    reply = sample_reply()
    q = next(q for q in reply["questions"] if q["id"] == "accident_type")
    for o in q["options"]:
        o["value"] = o["en"]                       # AI used labels instead of export values
    dup = copy.deepcopy(next(q for q in reply["questions"] if q["id"] == "sex"))
    reply["questions"].append(dup)                 # and repeated a box
    ai.append(reply)
    out = converter.convert(read_form(sample_pdf))
    acc = next(q for q in out["questions"] if q["fields"] == ["accident_type"])
    assert [o["value"] for o in acc["options"]] == ["MotorVehicle", "Work", "Fall", "Sports", "Other"]
    assert acc["options"][2]["ne"] == "चिप्लिएर वा लडेर"     # AI wording kept by position
    assert sum(q["fields"] == ["sex"] for q in out["questions"]) == 1
    assert len({q["id"] for q in out["questions"]}) == len(out["questions"])


def upload(pdf_bytes, name="Riverbend Physical Therapy", email="frontdesk@example.com"):
    return client.post("/api/forms", data={"clinic_name": name, "clinic_email": email},
                       files={"pdf": ("intake.pdf", pdf_bytes, "application/pdf")})


def test_upload_rejects_junk_and_flat_pdfs():
    assert upload(b"not a pdf").status_code == 400
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Name: ______")
    r = upload(doc.tobytes())
    assert r.status_code == 422 and "no fillable boxes" in r.json()["detail"]
    assert upload(b"%PDF", email="not-an-email").status_code == 422


def test_clinic_flow_upload_convert_edit_publish(sample_pdf, ai):
    r = upload(sample_pdf)
    assert r.status_code == 200
    made = r.json()
    assert made["box_count"] == 70 and made["pages"] == 5
    fid, key = made["id"], made["edit_key"]

    assert client.get(f"/api/forms/{fid}").status_code == 404          # patients can't see a draft
    assert client.post(f"/api/forms/{fid}/convert").status_code == 403  # no edit key

    ai.append(sample_reply())
    form = client.post(f"/api/forms/{fid}/convert", headers={"x-edit-key": key}).json()
    assert form["status"] == "draft" and "edit_key" not in form

    r = client.patch(f"/api/forms/{fid}", headers={"x-edit-key": key},
                     json={"questions": [{"id": "last_name", "ne": "तपाईंको थर (परिवारको नाम) के हो?", "fields": ["x"]}]})
    q = next(q for q in r.json()["questions"] if q["id"] == "last_name")
    assert q["ne"] == "तपाईंको थर (परिवारको नाम) के हो?" and q["fields"] == ["last_name"]   # wording only

    assert client.patch(f"/api/forms/{fid}", headers={"x-edit-key": "wrong"}, json={}).status_code == 403
    link = client.post(f"/api/forms/{fid}/publish", headers={"x-edit-key": key}).json()["link"]
    assert link.endswith(f"/f/{fid}")
    patient = client.get(f"/api/forms/{fid}").json()
    assert "clinic_email" not in patient and "edit_key" not in patient

    r = client.post(f"/api/forms/{fid}/submit", json={"answers": {"last_name": "Neupane"}, "signer_name": "Kamala Neupane"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


def test_convert_without_a_key_says_so(sample_pdf):
    made = upload(sample_pdf).json()
    r = client.post(f"/api/forms/{made['id']}/convert", headers={"x-edit-key": made["edit_key"]})
    assert r.status_code == 503


def test_sample_cannot_be_edited():
    assert client.patch("/api/forms/sample", headers={"x-edit-key": ""}, json={}).status_code == 403
