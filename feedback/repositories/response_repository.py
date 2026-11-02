"""Data access + analytics queries for Response entities (Model layer)."""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Avg, Count, QuerySet
from django.db.models.functions import TruncDate
from django.utils import timezone

from feedback.models import Response

_METRIC_FIELD = {
    "product": "q1",
    "care": "q2",
    "happy": "q3",
    "overall": "mean",
}


def _since(days: int):
    return timezone.now() - timedelta(days=days)


class ResponseRepository:
    def with_customer(self) -> QuerySet[Response]:
        return Response.objects.select_related("customer")

    def get_with_customer(self, response_id: int) -> Response | None:
        return self.with_customer().filter(pk=response_id).first()

    def list_with_customer(self, limit: int = 50, offset: int = 0) -> QuerySet[Response]:
        return self.with_customer().order_by("-created_at")[offset : offset + min(limit, 200)]

    def paginate_with_customer(
        self, page: int, page_size: int, classification: str | None = None
    ) -> tuple[list[Response], int]:
        """Return (page_items, total_count) ordered newest-first.

        Optionally filter by classification (detractor|passive|promoter).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        qs = self.with_customer()
        if classification in (Response.DETRACTOR, Response.PASSIVE, Response.PROMOTER):
            qs = qs.filter(classification=classification)
        total = qs.count()
        offset = (page - 1) * page_size
        items = list(qs.order_by("-created_at")[offset : offset + page_size])
        return items, total

    # --- analytics ---
    def count(self) -> int:
        return Response.objects.count()

    def count_since(self, days: int) -> int:
        return Response.objects.filter(created_at__gte=_since(days)).count()

    def average_mean(self) -> float | None:
        avg = Response.objects.aggregate(v=Avg("mean"))["v"]
        return round(float(avg), 2) if avg is not None else None

    def average_metric_since(self, metric: str, days: int) -> float | None:
        field = _METRIC_FIELD.get(metric, "mean")
        avg = Response.objects.filter(created_at__gte=_since(days)).aggregate(
            v=Avg(field)
        )["v"]
        return round(float(avg), 2) if avg is not None else None

    def classification_counts(self, days: int | None = None) -> dict[str, int]:
        qs = Response.objects.all()
        if days is not None:
            qs = qs.filter(created_at__gte=_since(days))
        rows = qs.values("classification").annotate(n=Count("id"))
        counts = {r["classification"]: r["n"] for r in rows}
        return {
            Response.DETRACTOR: counts.get(Response.DETRACTOR, 0),
            Response.PASSIVE: counts.get(Response.PASSIVE, 0),
            Response.PROMOTER: counts.get(Response.PROMOTER, 0),
        }

    def daily_trend(self, days: int) -> list[tuple[date, float, int]]:
        rows = (
            Response.objects.filter(created_at__gte=_since(days))
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(mean=Avg("mean"), n=Count("id"))
            .order_by("day")
        )
        return [(r["day"], round(float(r["mean"]), 2), r["n"]) for r in rows]
