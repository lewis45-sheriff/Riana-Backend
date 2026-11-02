"""Thin HTTP layer (DRF views) for auth: login, logout, me."""

from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.controllers import AuthController
from accounts.serializers import LoginSerializer
from accounts.services.jwt_service import (
    clear_auth_cookie,
    create_access_token,
    set_auth_cookie,
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        controller = AuthController()
        user = controller.login(
            serializer.validated_data["identifier"],
            serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=401)

        token = create_access_token(user.id)
        response = Response({"user": controller.serialize_user(user)})
        set_auth_cookie(response, token)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, _request: Request) -> Response:
        response = Response({"ok": True})
        clear_auth_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({"user": AuthController.serialize_user(request.user)})
