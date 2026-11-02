"""Data access for EmailLog entities (Model layer)."""

from __future__ import annotations

from django.db.models import QuerySet

from feedback.models import EmailLog


class EmailRepository:
    def paginate(self, page: int, page_size: int) -> tuple[list[EmailLog], int]:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        qs: QuerySet[EmailLog] = EmailLog.objects.all().order_by("-created_at")
        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset : offset + page_size]), total

    def get(self, email_id: int) -> EmailLog | None:
        return EmailLog.objects.filter(pk=email_id).first()
