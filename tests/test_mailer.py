import smtplib

import pytest

from app import mailer, settings

FORM = {"id": "sample", "clinic_name": "Riverbend Physical Therapy", "clinic_email": "frontdesk@example.com",
        "form_title_en": "New Patient Intake"}


class FakeSMTP:
    sent = []
    fail = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        if FakeSMTP.fail:
            raise smtplib.SMTPAuthenticationError(535, b"bad password")

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture
def send_mode(monkeypatch, tmp_path):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(settings, "MAIL_MODE", "send")
    monkeypatch.setattr(settings, "SMTP_USER", "contact@keepsrunning.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "MIN_SEND_GAP_SECONDS", 300)
    monkeypatch.setattr(settings, "OUTBOX_DIR", tmp_path)
    return tmp_path


def test_sends_then_holds_the_next_one(send_mode):
    assert mailer.deliver(FORM, b"%PDF-1.7", "Kamala Neupane", []) == "sent"
    assert FakeSMTP.sent[0]["To"] == "frontdesk@example.com"
    assert FakeSMTP.sent[0]["Subject"] == "Intake form: Kamala Neupane"
    # a second patient a moment later: held, not sent
    assert mailer.deliver(FORM, b"%PDF-1.7", "Ram Neupane", ["Member ID"]) == "deferred"
    assert len(FakeSMTP.sent) == 1
    assert len(list(send_mode.glob("*-deferred.eml"))) == 1
    assert 290 < mailer.seconds_until_next_send() <= 300


def test_failure_keeps_the_email(send_mode):
    FakeSMTP.fail = True
    assert mailer.deliver(FORM, b"%PDF-1.7", "Kamala Neupane", []) == "failed"
    assert len(list(send_mode.glob("*-failed.eml"))) == 1
    assert mailer.seconds_until_next_send() == 0      # a failed send doesn't start the wait


def test_missing_password_never_tries(send_mode, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    assert mailer.deliver(FORM, b"%PDF-1.7", "Kamala Neupane", []) == "failed"
    assert FakeSMTP.sent == []


def test_file_mode_never_sends(send_mode, monkeypatch):
    monkeypatch.setattr(settings, "MAIL_MODE", "file")
    assert mailer.deliver(FORM, b"%PDF-1.7", "Kamala Neupane", []) == "saved"
    assert FakeSMTP.sent == []
