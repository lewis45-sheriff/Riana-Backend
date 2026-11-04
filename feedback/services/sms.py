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

AT_SMS_URL = (
    "https://api.sandbox.africastalking.com/version1/messaging"
    if settings.AFRICASTALKING_USERNAME.lower() == "sandbox"
    else "https://api.africastalking.com/version1/messaging"
)

INVITE_TEMPLATE = (
    "Thanks for buying our paint! Rate us 1-5 for product, care and "
    "happiness. Reply e.g. 4 5 4"
)


class LiveAfricaTalkingConfigurationError(Exception):
    """Raised when live Africa's Talking credentials are unavailable."""


def is_mock() -> bool:
    if settings.SMS_PROVIDER == "smsgate":
        return False  # Missing gateway credentials must fail rather than simulate a send.
    return not settings.AFRICASTALKING_API_KEY


def send_sms(to: str, message: str) -> dict:
    """Send a single SMS. Returns a result dict. Never raises to the caller."""
    if settings.SMS_PROVIDER == "smsgate":
        from feedback.services.sim_gateway import send_message

        return send_message(to, message)
    if settings.SMS_PROVIDER != "africastalking":
        return {"status": "error", "error": "Unknown SMS provider configuration"}
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
        provider = resp.json()
        recipients = provider.get("SMSMessageData", {}).get("Recipients", [])
        accepted = bool(recipients) and all(
            r.get("statusCode") in {100, 101, 102} for r in recipients
        )
        return {"status": "accepted" if accepted else "error", "provider": provider}
    except Exception as exc:  # pragma: no cover - network dependent
        logger.exception("SMS send failed; continuing")
        return {"status": "error", "error": str(exc)}


def send_live_africastalking_sms(to: str, message: str) -> dict:
    """Send directly through Africa's Talking live API, bypassing provider selection."""
    username = settings.AFRICASTALKING_USERNAME.strip()
    api_key = settings.AFRICASTALKING_API_KEY.strip()
    if not username or not api_key:
        raise LiveAfricaTalkingConfigurationError(
            "Live Africa's Talking username and API key must be configured."
        )
    if username.lower() == "sandbox":
        raise LiveAfricaTalkingConfigurationError(
            "This endpoint requires a live Africa's Talking account, not the sandbox username."
        )

    headers = {
        "apiKey": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"username": username, "to": to, "message": message}
    if settings.AFRICASTALKING_SENDER_ID:
        data["from"] = settings.AFRICASTALKING_SENDER_ID

    try:
        response = httpx.post(
            "https://api.africastalking.com/version1/messaging",
            data=data,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        provider = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Africa's Talking rejected a live SMS request (HTTP %s).",
            exc.response.status_code,
        )
        return {
            "status": "error",
            "provider": "africastalking",
            "detail": f"Africa's Talking rejected the request (HTTP {exc.response.status_code}).",
        }
    except (httpx.HTTPError, ValueError):
        logger.exception("Could not confirm live SMS acceptance from Africa's Talking.")
        return {
            "status": "error",
            "provider": "africastalking",
            "detail": "Could not confirm acceptance from Africa's Talking.",
        }

    if not isinstance(provider, dict):
        return {
            "status": "error",
            "provider": "africastalking",
            "detail": "Africa's Talking returned an invalid response.",
        }
    message_data = provider.get("SMSMessageData")
    recipients = message_data.get("Recipients", []) if isinstance(message_data, dict) else []
    if not isinstance(recipients, list):
        recipients = []
    recipient_statuses = [
        {"statusCode": recipient.get("statusCode"), "status": recipient.get("status")}
        for recipient in recipients
        if isinstance(recipient, dict)
    ]
    accepted = bool(recipients) and all(
        isinstance(recipient, dict) and recipient.get("statusCode") in {100, 101, 102}
        for recipient in recipients
    )
    return {
        "status": "accepted" if accepted else "error",
        "provider": "africastalking",
        "detail": (
            "Accepted by Africa's Talking; delivery is not confirmed."
            if accepted
            else "Africa's Talking did not accept the SMS."
        ),
        "recipients": recipient_statuses,
    }


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
