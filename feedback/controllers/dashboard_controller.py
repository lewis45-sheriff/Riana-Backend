"""CONTROLLER: dashboard analytics (total, trend + projection, split)."""

from __future__ import annotations

from datetime import date, timedelta

from feedback.repositories.alert_repository import AlertRepository
from feedback.repositories.response_repository import ResponseRepository

PROJECTION_DAYS = 3


class DashboardController:
    def __init__(self) -> None:
        self.responses = ResponseRepository()
        self.alerts = AlertRepository()

    @staticmethod
    def _project(
        points: list[tuple[date, float]], future_days: int
    ) -> list[tuple[date, float]]:
        """Least-squares linear projection of the daily mean, clamped to 1-5."""
        if len(points) < 2:
            return []
        xs = list(range(len(points)))
        ys = [p[1] for p in points]
        n = len(xs)
        sx, sy = sum(xs), sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
        denom = n * sxx - sx * sx
        if denom == 0:
            return []
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        last_date = points[-1][0]
        out: list[tuple[date, float]] = []
        for i in range(1, future_days + 1):
            x = len(points) - 1 + i
            y = max(1.0, min(5.0, slope * x + intercept))
            out.append((last_date + timedelta(days=i), round(y, 2)))
        return out

    def summary(self, days: int = 14) -> dict:
        total = self.responses.count()
        average_mean = self.responses.average_mean()
        split = self.responses.classification_counts()

        rows = self.responses.daily_trend(days)
        trend: list[dict] = []
        actual_points: list[tuple[date, float]] = []
        for d_obj, mean_val, count in rows:
            trend.append(
                {"date": d_obj.isoformat(), "mean": mean_val, "count": count, "projected": False}
            )
            actual_points.append((d_obj, mean_val))

        for d_obj, y in self._project(actual_points, PROJECTION_DAYS):
            trend.append({"date": d_obj.isoformat(), "mean": y, "count": 0, "projected": True})

        return {
            "total_respondents": total,
            "average_mean": average_mean,
            "split": split,
            "trend": trend,
            "open_alerts": self.alerts.count_open(),
        }
