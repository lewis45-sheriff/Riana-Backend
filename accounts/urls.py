"""Auth URL routing."""

from __future__ import annotations

from django.urls import path

from accounts import views

urlpatterns = [
    path("login", views.LoginView.as_view()),
    path("logout", views.LogoutView.as_view()),
    path("me", views.MeView.as_view()),
]
