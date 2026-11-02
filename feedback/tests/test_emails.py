"""Tests for the email log + send-email-to-respondent endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from feedback.models import EmailLog

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def auth_client():
    User.objects.create_user(username="rep", password="pw12345", email="rep@x.com")
    c = Client()
    c.post(
        "/api/auth/login",
        data={"identifier": "rep", "password": "pw12345"},
        content_type="application/json",
    )
    return c


def _submit(client, **kw):
    payload = {"name": "T", "email": "t@example.com", "q1": 5, "q2": 5, "q3": 5}
    payload.update(kw)
    return client.post("/api/feedback", data=payload, content_type="application/json")


def test_emails_logged_on_submit(auth_client):
    # A promoter submission notifies the rep + auto thank-you => 2 email logs.
    _submit(Client())  # public submit (no auth needed)
    emails = auth_client.get("/api/emails").json()
    assert emails["total"] >= 1
    kinds = {e["kind"] for e in emails["items"]}
    assert kinds & {"alert", "thankyou"}


def test_emails_requires_auth():
    assert Client().get("/api/emails").status_code == 403


def test_send_email_to_promoter(auth_client):
    r = _submit(Client(), email="promo@example.com")
    rid = r.json()["response"]["id"]
    res = auth_client.post(
        f"/api/feedback/{rid}/send-email",
        data={"message": "Thanks so much!"},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["status"] in {"sent", "logged"}
    # The manual reply is recorded as a 'reply' email.
    assert EmailLog.objects.filter(kind="reply", to_email="promo@example.com").exists()


def test_draft_for_respondent(auth_client):
    r = _submit(Client(), email="d@example.com")
    rid = r.json()["response"]["id"]
    res = auth_client.post(f"/api/feedback/{rid}/draft")
    assert res.status_code == 200
    assert res.json()["draft"]
