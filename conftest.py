"""Pytest configuration.

Force email/SMS into offline mode during tests so the suite never makes real
network calls (SMTP, Africa's Talking) regardless of the developer's .env.
"""

import pytest


@pytest.fixture(autouse=True)
def _offline_integrations(settings):
    settings.SMTP_HOST = ""  # send_email -> console/log mode
    settings.AFRICASTALKING_API_KEY = ""  # sms -> mock mode
    settings.SMS_PROVIDER = "africastalking"
    settings.AI_PROVIDER = "mock"
