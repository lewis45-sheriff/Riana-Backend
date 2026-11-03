"""Exercise gateway authentication, deduplication, and transport without a real SIM."""

import hashlib
import hmac
import json
import time
from unittest.mock import Mock, patch

import httpx
import pytest
from django.test import Client

from feedback.models import Customer, GatewayReceipt, Response
from feedback.services import sms

pytestmark = pytest.mark.django_db
SECRET = "test-signing-key-with-more-than-32-characters"
URL = "/api/sms/gateway/inbound"


@pytest.fixture
def gateway(settings):
    settings.SMSGATE_WEBHOOK_SECRET = SECRET
    settings.SMSGATE_DEVICE_ID = "test-device"
    Customer.objects.create(name="Invited customer", phone="+254105054766")


def post_event(*, text="4 5 4", signature=None, timestamp=None, device="test-device"):
    data = {
        "id": "event-123",
        "deviceId": device,
        "event": "sms:received",
        "payload": {"sender": "0105054766", "message": text},
    }
    raw = json.dumps(data)
    timestamp = str(int(time.time())) if timestamp is None else timestamp
    signed = hmac.new(SECRET.encode(), (raw + timestamp).encode(), hashlib.sha256).hexdigest()
    return Client().post(
        URL,
        raw,
        content_type="application/json",
        HTTP_X_TIMESTAMP=timestamp,
        HTTP_X_SIGNATURE=signature if signature is not None else signed,
    )


def test_signed_reply_is_normalized_saved_and_deduplicated(gateway):
    result = post_event()
    assert result.status_code == 200
    assert result.json()["mean"] == 4.33
    assert Response.objects.get().customer.phone == "+254105054766"
    assert post_event().json()["duplicate"] is True
    assert Response.objects.count() == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"signature": "a" * 64},
        {"timestamp": "1"},
        {"device": "untrusted-device"},
    ],
)
def test_untrusted_events_rejected(gateway, kwargs):
    assert post_event(**kwargs).status_code == 403
    assert not Response.objects.exists()
    assert not GatewayReceipt.objects.exists()


def test_unconfigured_signing_fails_closed(settings):
    settings.SMSGATE_WEBHOOK_SECRET = ""
    assert post_event().status_code == 403


def test_uninvited_sender_ignored(gateway):
    Customer.objects.all().delete()
    result = post_event()
    assert result.status_code == 200
    assert not result.json()["ok"]
    assert not Response.objects.exists()


def test_invalid_rating_does_not_create_feedback(gateway):
    assert not post_event(text="6 4 5 4").json()["ok"]
    assert not Response.objects.exists()


def test_gateway_send_queues_without_claiming_delivery(settings):
    settings.SMS_PROVIDER = "smsgate"
    settings.SMSGATE_USERNAME = "test-user"
    settings.SMSGATE_PASSWORD = "test-password"
    settings.SMSGATE_DEVICE_ID = "test-device"
    response = Mock()
    response.json.return_value = {"id": "outbound-123", "state": "Pending"}
    with patch("feedback.services.sim_gateway.httpx.post", return_value=response) as post:
        result = sms.send_sms("+254105054766", "Rate us")
    assert result["status"] == "queued"
    assert post.call_args.kwargs["json"]["phoneNumbers"] == ["+254105054766"]
    assert post.call_args.kwargs["auth"] == ("test-user", "test-password")


def test_gateway_failure_has_no_paid_provider_fallback(settings):
    settings.SMS_PROVIDER = "smsgate"
    settings.SMSGATE_USERNAME = "test-user"
    settings.SMSGATE_PASSWORD = "test-password"
    with patch(
        "feedback.services.sim_gateway.httpx.post", side_effect=httpx.ConnectError("offline")
    ) as post:
        assert sms.send_sms("+254105054766", "Rate us")["status"] == "error"
    assert post.call_count == 1


@pytest.mark.parametrize(
    "code,expected", [(100, "accepted"), (101, "accepted"), (102, "accepted"), (406, "error")]
)
def test_africastalking_recipient_status_is_respected(settings, code, expected):
    settings.AFRICASTALKING_API_KEY = "test-key"
    response = Mock()
    response.json.return_value = {"SMSMessageData": {"Recipients": [{"statusCode": code}]}}
    with patch("feedback.services.sms.httpx.post", return_value=response):
        assert sms.send_sms("+254105054766", "Rate us")["status"] == expected
