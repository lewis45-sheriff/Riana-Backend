"""CONTROLLER: Africa's Talking SMS (invites + inbound 3-digit replies)."""

from __future__ import annotations

import logging

from feedback.controllers.feedback_controller import FeedbackController
from feedback.models import Customer
from feedback.repositories.customer_repository import CustomerRepository
from feedback.services import sms

logger = logging.getLogger("controller.sms")


class SMSController:
    def __init__(self) -> None:
        self.customers = CustomerRepository()

    def send_invite(self, phone: str, name: str | None = None) -> dict:
        if name and self.customers.by_phone(phone) is None:
            Customer.objects.create(name=name, phone=phone)
        result = sms.send_invite(phone)
        return {"ok": True, "result": result}

    def handle_inbound(self, from_: str, text: str) -> dict:
        parsed = sms.parse_three_digit_reply(text)
        if parsed is None:
            logger.info("Ignoring non-rating SMS from %s: %r", from_, text)
            return {"ok": False, "reason": "expected three digits 1-5"}

        q1, q2, q3 = parsed
        customer = self.customers.by_phone(from_) if from_ else None
        name = (
            customer.name
            if customer
            else (f"SMS {from_[-4:]}" if from_ else "SMS user")
        )

        response, alert_created = FeedbackController().submit(
            name=name,
            email=customer.email if customer else None,
            phone=from_ or None,
            q1=q1,
            q2=q2,
            q3=q3,
            source="sms",
        )
        return {
            "ok": True,
            "mean": float(response.mean),
            "classification": response.classification,
            "alert_created": alert_created,
        }
