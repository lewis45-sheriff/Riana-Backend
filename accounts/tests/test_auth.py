"""Auth flow tests: login sets cookie, me works, logout clears, bad creds 401."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="care", password="pw12345", email="care@x.com"
    )


def test_login_sets_cookie_and_returns_user(user):
    c = Client()
    res = c.post(
        "/api/auth/login",
        data={"identifier": "care", "password": "pw12345"},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "care"
    assert settings.JWT_COOKIE_NAME in res.cookies


def test_login_with_email(user):
    c = Client()
    res = c.post(
        "/api/auth/login",
        data={"identifier": "care@x.com", "password": "pw12345"},
        content_type="application/json",
    )
    assert res.status_code == 200


def test_login_bad_credentials(user):
    c = Client()
    res = c.post(
        "/api/auth/login",
        data={"identifier": "care", "password": "wrong"},
        content_type="application/json",
    )
    assert res.status_code == 401


def test_me_requires_auth():
    assert Client().get("/api/auth/me").status_code == 403


def test_me_after_login(user):
    c = Client()
    c.post(
        "/api/auth/login",
        data={"identifier": "care", "password": "pw12345"},
        content_type="application/json",
    )
    res = c.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "care@x.com"


def test_logout_clears_cookie(user):
    c = Client()
    c.post(
        "/api/auth/login",
        data={"identifier": "care", "password": "pw12345"},
        content_type="application/json",
    )
    res = c.post("/api/auth/logout")
    assert res.status_code == 200
    # After logout the protected endpoint is forbidden again.
    assert c.get("/api/auth/me").status_code == 403
