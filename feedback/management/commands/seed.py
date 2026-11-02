"""Seed realistic demo data so the dashboard is non-empty on first run.

Spreads responses across the last ~14 days with a mild upward trend, a mix of
detractors/passives/promoters, some comments, and a couple of SMS-sourced
responses. Detractors get alerts with an AI draft.

Usage:
    python manage.py seed           # seed only if empty
    python manage.py seed --force   # wipe and reseed
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from feedback.models import Alert, Customer, Response
from feedback.services import agent
from feedback.services.scoring import is_detractor, score

_NAMES = [
    ("Amara Okafor", "amara@example.com", "+254700000001"),
    ("Brian Mwangi", "brian@example.com", "+254700000002"),
    ("Chloe Dubois", "chloe@example.com", "+254700000003"),
    ("Daniel Kim", "daniel@example.com", "+254700000004"),
    ("Esther Njoki", "esther@example.com", "+254700000005"),
    ("Femi Adeyemi", "femi@example.com", "+254700000006"),
    ("Grace Wanjiru", "grace@example.com", "+254700000007"),
    ("Hassan Ali", "hassan@example.com", "+254700000008"),
    ("Ivy Chen", "ivy@example.com", "+254700000009"),
    ("James Otieno", "james@example.com", "+254700000010"),
    ("Kavya Rao", "kavya@example.com", "+254700000011"),
    ("Liam Murphy", "liam@example.com", "+254700000012"),
]

_COMMENTS = [
    "The colour was richer than I expected, lovely finish.",
    "Delivery took far too long and the tin was dented.",
    "Customer care sorted my refund quickly, thank you.",
    "Paint was fine but the price feels a bit steep.",
    "Coverage is excellent — one coat did the job.",
    None,
    None,
    "The painter I hired loved how smoothly it went on.",
    "Had to call twice before anyone picked up.",
    None,
]


def _ratings_for_day(day_index: int, total_days: int) -> tuple[int, int, int]:
    base = 2.6 + (day_index / max(total_days - 1, 1)) * 1.6  # ~2.6 -> ~4.2
    return tuple(max(1, min(5, round(random.gauss(base, 0.9)))) for _ in range(3))


class Command(BaseCommand):
    help = "Seed demo feedback data."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--force", action="store_true", help="Wipe and reseed.")

    def handle(self, *args, **options) -> None:
        if options["force"]:
            Alert.objects.all().delete()
            Response.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write("Cleared existing data.")

        if Response.objects.exists():
            self.stdout.write("Data already present; skipping (use --force to reseed).")
            return

        random.seed(42)
        total_days = 14
        now = timezone.now()
        inserted = 0

        for day_index in range(total_days):
            day = now - timedelta(days=(total_days - 1 - day_index))
            for _ in range(random.randint(2, 6)):
                name, email, phone = random.choice(_NAMES)
                source = "sms" if random.random() < 0.2 else "web"
                q1, q2, q3 = _ratings_for_day(day_index, total_days)
                mean, classification = score(q1, q2, q3)
                comment = None if source == "sms" else random.choice(_COMMENTS)

                customer, _ = Customer.objects.get_or_create(
                    email=email, defaults={"name": name, "phone": phone}
                )
                created = day.replace(
                    hour=random.randint(8, 19), minute=random.randint(0, 59)
                )
                response = Response.objects.create(
                    customer=customer,
                    source=source,
                    q1=q1,
                    q2=q2,
                    q3=q3,
                    comment=comment,
                    mean=mean,
                    classification=classification,
                )
                Response.objects.filter(pk=response.pk).update(created_at=created)
                inserted += 1

                if is_detractor(classification):
                    try:
                        draft, _d = agent.draft_reply(customer, response)
                    except Exception:
                        draft = None
                    Alert.objects.create(
                        response=response,
                        customer=customer,
                        channels="in_app,email",
                        ai_draft=draft,
                    )

        self.stdout.write(self.style.SUCCESS(f"Seeded {inserted} responses."))
