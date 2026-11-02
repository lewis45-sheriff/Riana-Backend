"""Data access for Alert entities (Model layer)."""

from __future__ import annotations

from django.db.models import QuerySet

from feedback.models import Alert


class AlertRepository:
    def get(self, alert_id: int) -> Alert | None:
        return (
            Alert.objects.select_related("customer", "response", "response__customer")
            .filter(pk=alert_id)
            .first()
        )

    def list(self, status: str | None = None) -> QuerySet[Alert]:
        qs = Alert.objects.select_related(
            "customer", "response", "response__customer"
        ).order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        return qs

    def count_open(self) -> int:
        return Alert.objects.filter(status=Alert.STATUS_NEW).count()
