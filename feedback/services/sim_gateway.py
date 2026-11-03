"""SMSGate Android cloud transport and signed incoming-message handling."""

import hashlib
import hmac
import re
import time

import httpx
from django.conf import settings
from django.db import transaction

from feedback.controllers.sms_controller import SMSController
from feedback.models import Customer, GatewayReceipt


def send_message(phone: str, message: str) -> dict:
    if not settings.SMSGATE_USERNAME or not settings.SMSGATE_PASSWORD:
        return {"status": "error", "error": "Android gateway credentials are not configured"}
    payload = {"textMessage": {"text": message}, "phoneNumbers": [phone]}
    if settings.SMSGATE_DEVICE_ID:
        payload["deviceId"] = settings.SMSGATE_DEVICE_ID
    try:
        response = httpx.post(
            settings.SMSGATE_BASE_URL.rstrip("/") + "/messages",
            auth=(settings.SMSGATE_USERNAME, settings.SMSGATE_PASSWORD),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not data.get("id"):
            return {"status": "error", "error": "Gateway returned no message ID"}
        return {"status": "queued", "message_id": data["id"], "transport": "smsgate"}
    except (httpx.HTTPError, ValueError):
        # Do not log credential-bearing requests or retry ambiguous submissions automatically.
        return {"status": "error", "error": "Gateway submission could not be confirmed"}


def valid_signature(body: bytes, timestamp: str, signature: str) -> bool:
    secret = settings.SMSGATE_WEBHOOK_SECRET
    if len(secret) < 32 or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False
    expected = hmac.new(secret.encode(), body + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())


def normalize_phone(phone: str) -> str:
    phone = re.sub(r"[\s()-]", "", phone)
    if re.fullmatch(r"0[17]\d{8}", phone):
        return "+254" + phone[1:]
    if re.fullmatch(r"254[17]\d{8}", phone):
        return "+" + phone
    return phone


@transaction.atomic
def receive(data: dict) -> dict:
    receipt, created = GatewayReceipt.objects.get_or_create(
        device_id=data["deviceId"],
        event_id=data["id"],
    )
    if not created:
        return {**receipt.result, "duplicate": True}
    payload = data["payload"]
    phone = normalize_phone(payload["sender"])
    text = payload["message"]
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        result = {"ok": False, "reason": "invalid sender number"}
    elif not Customer.objects.filter(phone=phone).exists():
        result = {"ok": False, "reason": "sender has not been invited"}
    elif not re.fullmatch(r"\s*[1-5](?:[\s,-]*[1-5]){2}\s*", text):
        result = {"ok": False, "reason": "reply with exactly three ratings from 1 to 5"}
    else:
        result = SMSController().handle_inbound(phone, text)
    receipt.result = result
    receipt.save(update_fields=["result"])
    return result
