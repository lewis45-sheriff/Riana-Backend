"""CONTROLLER: detractor alerts (list, acknowledge, regenerate AI draft)."""

from __future__ import annotations

from feedback.models import Alert
from feedback.repositories.alert_repository import AlertRepository
from feedback.services import agent, notifications, sms


class AlertController:
    def __init__(self) -> None:
        self.alerts = AlertRepository()

    def list(self, status: str | None = None):
        return self.alerts.list(status)

    def get(self, alert_id: int) -> Alert | None:
        return self.alerts.get(alert_id)

    def acknowledge(self, alert_id: int, status: str) -> Alert | None:
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        alert.status = status
        alert.save(update_fields=["status"])
        return alert

    def regenerate_draft(self, alert_id: int) -> tuple[str, bool] | None:
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        draft, degraded = agent.draft_reply(alert.response.customer, alert.response)
        alert.ai_draft = draft
        alert.save(update_fields=["ai_draft"])
        return draft, degraded

    def _record_channel(self, alert: Alert, channel: str) -> None:
        """Append a channel to the alert's csv list and mark it acknowledged."""
        channels = [c for c in (alert.channels or "").split(",") if c]
        if channel not in channels:
            channels.append(channel)
        alert.channels = ",".join(channels)
        if alert.status == Alert.STATUS_NEW:
            alert.status = Alert.STATUS_ACK
        alert.save(update_fields=["channels", "status"])

    def send_email_reply(self, alert_id: int, message: str | None = None) -> dict | None:
        """Email the follow-up reply to the customer. Returns a result dict."""
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        body = message or alert.ai_draft or ""
        if not body.strip():
            return {"status": "error", "reason": "no message to send"}
        result = notifications.send_reply_to_customer(alert.response.customer, body)
        if result.get("status") in {"sent", "logged"}:
            self._record_channel(alert, "email_reply")
        return result

    def send_sms_reply(self, alert_id: int, message: str | None = None) -> dict | None:
        """Text the follow-up reply to the customer via Africa's Talking."""
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        phone = alert.response.customer.phone
        if not phone:
            return {"status": "skipped", "reason": "customer has no phone number"}
        body = message or alert.ai_draft or ""
        if not body.strip():
            return {"status": "error", "reason": "no message to send"}
        # SMS is short — keep to a sensible length.
        result = sms.send_sms(phone, body[:320])
        if result.get("status") in {"sent", "mock"}:
            self._record_channel(alert, "sms_reply")
        return {"status": result.get("status"), "to": phone, "provider": result}
