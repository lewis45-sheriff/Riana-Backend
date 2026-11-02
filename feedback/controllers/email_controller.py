"""CONTROLLER: sent-email log (list + detail)."""

from __future__ import annotations

import math

from feedback.repositories.email_repository import EmailRepository


class EmailController:
    def __init__(self) -> None:
        self.emails = EmailRepository()

    def paginate(self, page: int, page_size: int) -> dict:
        items, total = self.emails.paginate(page, page_size)
        page_count = max(1, math.ceil(total / page_size)) if page_size else 1
        return {
            "items": items,
            "total": total,
            "page": max(1, page),
            "page_size": page_size,
            "page_count": page_count,
        }

    def get(self, email_id: int):
        return self.emails.get(email_id)
