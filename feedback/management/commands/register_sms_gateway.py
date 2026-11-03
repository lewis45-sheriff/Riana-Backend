"""Register the Android device's signed incoming SMS webhook."""

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Register the SMSGate sms:received callback (does not send SMS)."

    def add_arguments(self, parser):
        parser.add_argument("--url", default="https://34.207.109.162/api/sms/gateway/inbound")

    def handle(self, *args, **options):
        if not options["url"].startswith("https://"):
            raise CommandError("The callback URL must use HTTPS")
        if not (settings.SMSGATE_USERNAME and settings.SMSGATE_PASSWORD):
            raise CommandError("Configure SMSGATE_USERNAME and SMSGATE_PASSWORD first")
        if len(settings.SMSGATE_WEBHOOK_SECRET) < 32:
            raise CommandError(
                "Set SMSGATE_WEBHOOK_SECRET to the phone's signing key (32+ characters)"
            )
        payload = {"id": "riana-survey-replies", "url": options["url"], "event": "sms:received"}
        if settings.SMSGATE_DEVICE_ID:
            payload["device_id"] = settings.SMSGATE_DEVICE_ID
        try:
            response = httpx.post(
                settings.SMSGATE_BASE_URL.rstrip("/") + "/webhooks",
                auth=(settings.SMSGATE_USERNAME, settings.SMSGATE_PASSWORD),
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            raise CommandError(
                "Webhook registration failed; check gateway credentials and connectivity"
            ) from None
        self.stdout.write(
            self.style.SUCCESS("Incoming SMS webhook registered. Allow it to sync to the phone.")
        )
