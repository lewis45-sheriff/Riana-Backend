"""Africa's Talking SMS integration.

Runs in *mock mode* when no API key is set (logs instead of sending), so the
system works end to end in local/demo/CI without credentials.

Docs: https://developers.africastalking.com/docs/sms/sending/bulk
"""

from __future__ import annotations

import logging
import re

import httpx
from django.conf import settings

logger = logging.getLogger("sms")

AT_SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"

INVITE_TEMPLATE = (
    "Thanks for buying our paint! Rate us 1-5 for product, care and "
    "happiness. Reply e.g. 4 5 4"
)


def is_mock() -> bool:
    return not settings.AFRICASTALKING_API_KEY


def send_sms(to: str, message: str) -> dict:
    """Send a single SMS. Returns a result dict. Never raises to the caller."""
    if is_mock():
        logger.info("[sms:mock] to=%s message=%s", to, message)
        return {"status": "mock", "to": to, "message": message}
    try:
        headers = {
            "apiKey": settings.AFRICASTALKING_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {
            "username": settings.AFRICASTALKING_USERNAME,
            "to": to,
            "message": message,
        }
        if settings.AFRICASTALKING_SENDER_ID:
            data["from"] = settings.AFRICASTALKING_SENDER_ID
        resp = httpx.post(AT_SMS_URL, data=data, headers=headers, timeout=15)
        resp.raise_for_status()
        return {"status": "sent", "provider": resp.json()}
    except Exception as exc:  # pragma: no cover - network dependent
        logger.exception("SMS send failed; continuing")
        return {"status": "error", "error": str(exc)}


def send_invite(to: str) -> dict:
    return send_sms(to, INVITE_TEMPLATE)


def parse_three_digit_reply(text: str) -> tuple[int, int, int] | None:
    """Parse an inbound reply like '4 5 4' or '454' into (q1, q2, q3).

    Returns None if the message does not contain exactly three digits in 1-5.
    """
    digits = re.findall(r"[1-5]", text or "")
    if len(digits) != 3:
        return None
    q1, q2, q3 = (int(d) for d in digits)
    return q1, q2, q3
