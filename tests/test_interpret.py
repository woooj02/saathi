import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app import answers, gemini, settings
from app.main import app

client = TestClient(app)
TODAY = dt.date(2026, 10, 24)


@pytest.fixture
def fake_ai(monkeypatch):
    """Replace Gemini with canned replies; records the prompts it was sent."""
    calls = []

    def install(reply):
        def fake(prompt, schema, **kw):
            calls.append(prompt)
            return reply
        monkeypatch.setattr(gemini, "generate_json", fake)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        return calls
    return install


def question(qid):
    form = client.get("/api/forms/sample").json()
    return next(q for q in form["questions"] if q["id"] == qid)


def test_text_answer(fake_ai):
    calls = fake_ai({"ok": True, "said_ne": "काममा पार्किङमा बरफमा चिप्लिएँ।", "en": "I slipped on ice in the parking lot at work."})
    r = answers.interpret(question("injury_description"), "काम मा पार्किङ मा बरफ मा चिप्लिएँ", today=TODAY)
    assert r == {"ok": True, "said": "काममा पार्किङमा बरफमा चिप्लिएँ।", "en": "I slipped on ice in the parking lot at work.",
                 "value": "I slipped on ice in the parking lot at work."}
    assert "In your own words, how did the injury happen?" in calls[0]
    assert "2083-07-07" in calls[0]   # today's date is given in both calendars for relative dates


def test_name_is_romanised(fake_ai):
    fake_ai({"ok": True, "said_ne": "न्यौपाने", "en": "Neupane"})
    assert answers.interpret(question("last_name"), "न्यौपाने", today=TODAY)["value"] == "Neupane"


def test_bs_date_is_converted_by_code(fake_ai):
    fake_ai({"ok": True, "said_ne": "२०२१ पुस ३०", "en": "30 Poush 2021", "calendar": "BS", "year": 2021, "month": 9, "day": 30})
    r = answers.interpret(question("date_of_birth"), "दुई हजार एक्काइस पुस तीस", today=TODAY)
    assert r["value"] == "01/13/1965"
    assert r["said"] == "२०२१ पुस ३०"
    assert r["parts"] == {"calendar": "BS", "year": 2021, "month": 9, "day": 30}


def test_impossible_date_is_not_accepted(fake_ai):
    fake_ai({"ok": True, "said_ne": "", "en": "", "calendar": "BS", "year": 2081, "month": 1, "day": 40})
    assert answers.interpret(question("injury_date"), "...", today=TODAY) == {"ok": False}


def test_phone_digits_are_formatted(fake_ai):
    fake_ai({"ok": True, "said_ne": "तीन शून्य तीन ...", "en": "३०३ 555 0142"})
    assert answers.interpret(question("phone"), "तीन शून्य तीन", today=TODAY)["value"] == "(303) 555-0142"


def test_not_understood(fake_ai):
    fake_ai({"ok": False, "said_ne": "", "en": ""})
    assert answers.interpret(question("medications"), "उम्म", today=TODAY) == {"ok": False}


def test_english_side_must_be_english(fake_ai):
    fake_ai({"ok": True, "said_ne": "दम", "en": "दम"})
    assert answers.interpret(question("allergies"), "दम", today=TODAY) == {"ok": False}


def test_route_needs_a_key():
    r = client.post("/api/forms/sample/interpret", json={"question_id": "medications", "transcript": "औषधि"})
    assert r.status_code == 503
    assert client.get("/api/health").json()["ai"] is False


def test_route_with_fake_ai(fake_ai):
    fake_ai({"ok": True, "said_ne": "एम्लोडिपिन ५ मिलिग्राम दिनको एक पटक", "en": "Amlodipine 5 mg once a day"})
    r = client.post("/api/forms/sample/interpret", json={"question_id": "medications", "transcript": "एम्लोडिपिन पाँच एमजी"})
    assert r.status_code == 200 and r.json()["en"] == "Amlodipine 5 mg once a day"
    assert client.post("/api/forms/sample/interpret", json={"question_id": "sex", "transcript": "महिला"}).status_code == 422
    assert client.post("/api/forms/sample/interpret", json={"question_id": "nope", "transcript": "x"}).status_code == 404


def test_ai_failure_is_a_502(monkeypatch):
    def boom(*a, **k):
        raise gemini.AIError("quota")
    monkeypatch.setattr(gemini, "generate_json", boom)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    r = client.post("/api/forms/sample/interpret", json={"question_id": "medications", "transcript": "औषधि"})
    assert r.status_code == 502


def test_parse_strips_code_fences():
    assert gemini._parse('```json\n{"ok": true}\n```') == {"ok": True}
    with pytest.raises(ValueError):
        gemini._parse("[1, 2]")
