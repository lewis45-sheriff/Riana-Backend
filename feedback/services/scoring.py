"""Core scoring domain logic.

Rules (from the brief):
    mean < 3      -> detractor (triggers an alert)
    mean == 3.00  -> passive   (exact 3.00 only)
    mean > 3      -> promoter
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

DETRACTOR = "detractor"
PASSIVE = "passive"
PROMOTER = "promoter"


def compute_mean(q1: int, q2: int, q3: int) -> Decimal:
    """Mean of the three answers, rounded to 2 decimals."""
    total = Decimal(q1) + Decimal(q2) + Decimal(q3)
    return (total / Decimal(3)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def classify(mean: Decimal | float | str) -> str:
    """Classify a mean into detractor / passive / promoter."""
    m = Decimal(str(mean)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if m < Decimal("3.00"):
        return DETRACTOR
    if m == Decimal("3.00"):
        return PASSIVE
    return PROMOTER


def score(q1: int, q2: int, q3: int) -> tuple[Decimal, str]:
    """Return (mean, classification) for three 1..5 answers."""
    mean = compute_mean(q1, q2, q3)
    return mean, classify(mean)


def is_detractor(classification: str) -> bool:
    return classification == DETRACTOR
