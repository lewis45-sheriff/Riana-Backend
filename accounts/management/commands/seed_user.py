"""Create a default care-rep login so the dashboard is reachable out of the box.

Credentials come from env (DEMO_USER / DEMO_PASSWORD) or default to
care@companyx.example / changeme123. Safe to run repeatedly.
"""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update the default care-rep user."

    def handle(self, *args, **options) -> None:
        username = os.environ.get("DEMO_USER", "care")
        email = os.environ.get("DEMO_EMAIL", "care@companyx.example")
        password = os.environ.get("DEMO_PASSWORD", "changeme123")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": "Care", "last_name": "Rep", "is_staff": True},
        )
        user.email = email
        user.is_staff = True
        user.set_password(password)
        user.save()

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} user '{username}' (password set)."))
