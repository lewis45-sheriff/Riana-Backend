"""Root URL configuration."""

from __future__ import annotations

from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok"})


def root(_request):
    return JsonResponse({"service": "Company X Feedback API", "framework": "django"})


urlpatterns = [
    path("", root),
    path("health", health),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("feedback.urls")),
]
