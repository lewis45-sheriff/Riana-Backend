"""CONTROLLER: feedback submission flow (persist -> score -> alert).

Used by BOTH the web form and SMS replies so scoring and alerting behave
identically regardless of channel. Notifications and AI drafts are best-effort
and never block the save.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from feedback.models import Alert, Response
from feedback.repositories.customer_repository import CustomerRepository
from feedback.repositories.response_repository import ResponseRepository
from feedback.services import agent, notifications
from feedback.services.scoring import is_detractor, score

logger = logging.getLogger("controller.feedback")


class FeedbackController:
    def __init__(self) -> None:
        self.customers = CustomerRepository()
        self.responses = ResponseRepository()

    @transaction.atomic
    def submit(
        self,
        *,
        name: str,
        email: str | None,
        phone: str | None,
        q1: int,
        q2: int,
        q3: int,
        comment: str | None = None,
        source: str = "web",
    ) -> tuple[Response, bool]:
        mean, classification = score(q1, q2, q3)
        customer = self.customers.find_or_create(name, email, phone)

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

        alert_created = False
        if is_detractor(classification):
            # Unhappy customer: create an alert, notify the rep, draft a reply
            # for manual review (human-in-the-loop — no auto-send to the customer).
            self._raise_alert(customer, response)
            alert_created = True
        else:
            # Satisfactory feedback (promoter/passive): notify the rep and
            # auto-send an AI thank-you to the customer. Best-effort.
            self._notify_care(customer, response)
            self._auto_thankyou(customer, response)

        return response, alert_created

    def _raise_alert(self, customer, response: Response) -> None:
        alert = Alert.objects.create(response=response, customer=customer)
        try:
            channels = notifications.notify_care_rep(customer, response)
            alert.channels = ",".join(channels)
        except Exception:
            logger.exception("Notification failed; alert still recorded")
        try:
            draft, _ = agent.draft_reply(customer, response)
            alert.ai_draft = draft
        except Exception:
            logger.exception("AI draft failed; alert still recorded")
        alert.save()

    @staticmethod
    def _notify_care(customer, response: Response) -> None:
        """Email the care rep a notification for satisfactory feedback."""
        if not settings.NOTIFY_CARE_ON_ALL:
            return
        try:
            notifications.notify_care_rep(customer, response)
        except Exception:
            logger.exception("Care-rep notification failed; continuing")

    @staticmethod
    def _auto_thankyou(customer, response: Response) -> None:
        """Auto-send an AI-drafted thank-you to a satisfied customer."""
        if not settings.AUTO_THANKYOU_ENABLED or not customer.email:
            return
        try:
            body, _ = agent.draft_thankyou(customer, response)
            notifications.send_thankyou_to_customer(customer, body)
        except Exception:
            logger.exception("Auto thank-you failed; continuing")

    def list(self, limit: int, offset: int):
        return self.responses.list_with_customer(limit, offset)

    def paginate(
        self, page: int, page_size: int, classification: str | None = None
    ) -> dict:
        import math

        items, total = self.responses.paginate_with_customer(
            page, page_size, classification
        )
        page_count = max(1, math.ceil(total / page_size)) if page_size else 1
        return {
            "items": items,
            "total": total,
            "page": max(1, page),
            "page_size": page_size,
            "page_count": page_count,
        }

    def get(self, response_id: int) -> Response | None:
        return self.responses.get_with_customer(response_id)

    def generate_email_draft(self, response_id: int) -> tuple[str, bool] | None:
        """AI-draft an email body appropriate to the respondent's rating."""
        response = self.responses.get_with_customer(response_id)
        if response is None:
            return None
        if is_detractor(response.classification):
            return agent.draft_reply(response.customer, response)
        return agent.draft_thankyou(response.customer, response)

    def send_email_to_respondent(
        self, response_id: int, message: str | None = None
    ) -> dict | None:
        """Email a respondent (any rating). Uses the given body or an AI draft."""
        response = self.responses.get_with_customer(response_id)
        if response is None:
            return None
        customer = response.customer
        if not customer.email:
            return {"status": "skipped", "reason": "customer has no email"}
        body = message
        if not body or not body.strip():
            if is_detractor(response.classification):
                body, _ = agent.draft_reply(customer, response)
            else:
                body, _ = agent.draft_thankyou(customer, response)
        return notifications.send_reply_to_customer(customer, body)
