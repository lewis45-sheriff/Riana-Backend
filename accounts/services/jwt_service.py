"""JWT encode/decode + cookie helpers for the auth module.

Tokens are short-lived access tokens carried in an httpOnly cookie so the
browser JS never touches them (mitigates XSS token theft).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_ACCESS_TTL_SECONDS),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        max_age=settings.JWT_ACCESS_TTL_SECONDS,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookie(response) -> None:
    response.delete_cookie(
        key=settings.JWT_COOKIE_NAME,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
