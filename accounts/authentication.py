"""DRF authentication that reads a JWT from an httpOnly cookie."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication

from accounts.services.jwt_service import decode_token

User = get_user_model()


class JWTCookieAuthentication(BaseAuthentication):
    """Authenticate a request from the JWT stored in the auth cookie.

    Treats a missing, invalid, expired, or orphaned token as anonymous
    (returns None) rather than raising. This is deliberate: raising
    AuthenticationFailed happens *before* a view's permission check, which
    would make even AllowAny endpoints (like /login) reject requests that
    carry a stale cookie — locking the user out with no way to re-authenticate.
    Protected endpoints still return 403 because request.user stays anonymous.
    """

    def authenticate(self, request):
        token = request.COOKIES.get(settings.JWT_COOKIE_NAME)
        if not token:
            # Also accept a bearer token (useful for tests / API clients).
            header = request.META.get("HTTP_AUTHORIZATION", "")
            if header.startswith("Bearer "):
                token = header.split(" ", 1)[1]
        if not token:
            return None

        payload = decode_token(token)
        if payload is None or payload.get("type") != "access":
            return None

        try:
            user = User.objects.get(pk=int(payload["sub"]), is_active=True)
        except (User.DoesNotExist, KeyError, ValueError):
            return None

        return (user, None)
