"""CONTROLLER: authentication orchestration."""

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


class AuthController:
    def login(self, identifier: str, password: str):
        """Authenticate by username or email. Returns the user or None."""
        username = identifier
        # Allow logging in with email.
        if "@" in identifier:
            match = User.objects.filter(email__iexact=identifier).first()
            if match:
                username = match.get_username()
        user = authenticate(username=username, password=password)
        if user is None or not user.is_active:
            return None
        return user

    @staticmethod
    def serialize_user(user) -> dict:
        return {
            "id": user.id,
            "username": user.get_username(),
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "is_staff": user.is_staff,
        }
