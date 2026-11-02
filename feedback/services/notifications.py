"""Email + in-app notifications for detractor alerts.

Fails gracefully: if SMTP is not configured or the send fails, we log and
continue. The alert row is still created so the care rep sees it in-app.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from django.conf import settings

logger = logging.getLogger("notifications")


_SUBJECT_PREFIX = {
    "detractor": "[Feedback alert] Unhappy customer",
    "passive": "[Feedback] Neutral response",
    "promoter": "[Feedback] Happy customer",
}

_INTRO = {
    "detractor": "A customer left feedback below the detractor threshold.",
    "passive": "A customer left neutral feedback.",
    "promoter": "A customer left positive feedback.",
}


def build_notification_email(customer, response) -> tuple[str, str]:
    """Build the care-rep notification email for any feedback classification."""
    cls = response.classification
    subject = f"{_SUBJECT_PREFIX.get(cls, '[Feedback]')}: {customer.name}"
    body = (
        f"{_INTRO.get(cls, 'A customer left feedback.')}\n\n"
        f"Name:  {customer.name}\n"
        f"Email: {customer.email or '-'}\n"
        f"Phone: {customer.phone or '-'}\n\n"
        f"Scores (1-5): product={response.q1}, care={response.q2}, "
        f"happy={response.q3}\n"
        f"Mean: {response.mean}  ->  {cls.upper()}\n"
    )
    if response.comment:
        body += f"\nComment:\n{response.comment}\n"
    if cls == "detractor":
        body += "\nFollow up with this customer as soon as possible."
    return subject, body


def _log_email(to: str, subject: str, body: str, kind: str, status: str, customer=None) -> None:
    """Persist a record of an outgoing email. Never raises to the caller."""
    try:
        from feedback.models import EmailLog

        EmailLog.objects.create(
            to_email=to or "",
            subject=subject,
            body=body,
            kind=kind,
            status=status,
            customer=customer,
        )
    except Exception:
        logger.exception("Failed to record EmailLog; continuing")


def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
    kind: str = "other",
    customer=None,
) -> bool:
    """Send an email via SMTP and record it in the email log.

    Returns True if actually sent, False if only logged (SMTP not configured).
    """
    if not settings.SMTP_HOST:
        logger.info("[email:console] to=%s subject=%s\n%s", to, subject, body)
        _log_email(to, subject, body, kind, "logged", customer)
        return False
    try:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        _log_email(to, subject, body, kind, "sent", customer)
        return True
    except Exception:  # pragma: no cover - network dependent
        logger.exception("Failed to send email; continuing")
        _log_email(to, subject, body, kind, "failed", customer)
        return False


def notify_care_rep(customer, response) -> list[str]:
    """Email the care rep a notification for this feedback. Returns channels."""
    channels = ["in_app"]  # the Alert row itself is the in-app notification
    subject, body = build_notification_email(customer, response)
    send_email(settings.CARE_REP_EMAIL, subject, body, kind="alert", customer=customer)
    channels.append("email")  # console mode counts as an email attempt in demo
    return channels


def send_reply_to_customer(customer, body: str) -> dict:
    """Email a follow-up (e.g. the AI draft) to the customer.

    The care rep is set as Reply-To so responses come back to the team.
    Returns a result dict; never raises to the caller.
    """
    if not customer.email:
        return {"status": "skipped", "reason": "customer has no email"}

    subject = "Following up on your feedback — Company X"
    sent = send_email(
        to=customer.email,
        subject=subject,
        body=body,
        reply_to=settings.CARE_REP_EMAIL,
        kind="reply",
        customer=customer,
    )
    return {"status": "sent" if sent else "logged", "to": customer.email}


def send_thankyou_to_customer(customer, body: str) -> dict:
    """Email an automated thank-you to a satisfied customer."""
    if not customer.email:
        return {"status": "skipped", "reason": "customer has no email"}

    subject = "Thanks for your feedback — Company X"
    sent = send_email(
        to=customer.email,
        subject=subject,
        body=body,
        reply_to=settings.CARE_REP_EMAIL,
        kind="thankyou",
        customer=customer,
    )
    return {"status": "sent" if sent else "logged", "to": customer.email}
