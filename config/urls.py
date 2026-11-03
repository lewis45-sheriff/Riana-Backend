"""Root URL configuration."""

from __future__ import annotations

from django.http import JsonResponse
from django.urls import include, path

from config.api_docs import schema, swagger


def health(_request):
    return JsonResponse({"status": "ok"})


def root(_request):
    return JsonResponse({"service": "Company X Feedback API", "framework": "django"})


urlpatterns = [
    path("api/docs/", swagger, name="swagger-ui"),
    path("api/schema/", schema, name="openapi-schema"),
    path("", root),
    path("health", health),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("feedback.urls")),
]
