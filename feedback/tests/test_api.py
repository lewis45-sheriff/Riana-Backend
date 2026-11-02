"""End-to-end API tests (pytest-django, SQLite test DB)."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def client():
    """Anonymous client (public endpoints)."""
    return Client()


@pytest.fixture
def auth_client():
    """Client logged in as a care rep — carries the JWT auth cookie."""
    User.objects.create_user(username="rep", password="pw12345", email="rep@x.com")
    c = Client()
    res = c.post(
        "/api/auth/login",
        data={"identifier": "rep", "password": "pw12345"},
        content_type="application/json",
    )
    assert res.status_code == 200
    return c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_submit_detractor_creates_alert(client, auth_client):
    r = client.post(
        "/api/feedback",
        data={"name": "Test User", "email": "t@example.com", "q1": 2, "q2": 3, "q3": 2},
        content_type="application/json",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["classification"] == "detractor"
    assert body["mean"] == 2.33
    assert body["alert_created"] is True

    alerts = auth_client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["customer"]["email"] == "t@example.com"
    assert alerts[0]["ai_draft"]  # smart-reply draft generated


def test_submit_promoter_no_alert(client):
    r = client.post(
        "/api/feedback",
        data={"name": "Happy", "email": "h@example.com", "q1": 5, "q2": 4, "q3": 5},
        content_type="application/json",
    )
    assert r.json()["alert_created"] is False


def test_passive_exact_three(client):
    r = client.post(
        "/api/feedback",
        data={"name": "Mid", "q1": 2, "q2": 4, "q3": 3},
        content_type="application/json",
    )
    assert r.json()["classification"] == "passive"


def test_dashboard_summary(client, auth_client):
    client.post(
        "/api/feedback",
        data={"name": "A", "q1": 1, "q2": 2, "q3": 2},
        content_type="application/json",
    )
    client.post(
        "/api/feedback",
        data={"name": "B", "q1": 4, "q2": 5, "q3": 4},
        content_type="application/json",
    )
    s = auth_client.get("/api/dashboard/summary").json()
    assert s["total_respondents"] == 2
    assert s["split"]["detractor"] == 1
    assert s["split"]["promoter"] == 1


def test_dashboard_requires_auth(client):
    assert client.get("/api/dashboard/summary").status_code == 403


def test_alerts_requires_auth(client):
    assert client.get("/api/alerts").status_code == 403


def test_sms_inbound(client):
    r = client.post(
        "/api/sms/inbound",
        data={"from": "+254700999999", "text": "4 5 4"},
        content_type="application/json",
    )
    body = r.json()
    assert body["ok"] is True
    assert body["classification"] == "promoter"


def test_sms_inbound_rejects_bad(client):
    r = client.post(
        "/api/sms/inbound",
        data={"from": "+254700999999", "text": "hello"},
        content_type="application/json",
    )
    assert r.json()["ok"] is False


def test_ai_ask(client, auth_client):
    client.post(
        "/api/feedback",
        data={"name": "A", "q1": 4, "q2": 4, "q3": 4},
        content_type="application/json",
    )
    r = auth_client.post(
        "/api/ai/ask",
        data={"question": "How did we do this week?"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert "answer" in r.json()


def test_alert_acknowledge(client, auth_client):
    client.post(
        "/api/feedback",
        data={"name": "Sad", "email": "s@example.com", "q1": 1, "q2": 1, "q3": 2},
        content_type="application/json",
    )
    alert_id = auth_client.get("/api/alerts").json()[0]["id"]
    r = auth_client.post(
        f"/api/alerts/{alert_id}/ack",
        data={"status": "acknowledged"},
        content_type="application/json",
    )
    assert r.json()["status"] == "acknowledged"
