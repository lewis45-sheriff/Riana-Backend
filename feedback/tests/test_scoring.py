"""Tests for the core scoring rules."""

from decimal import Decimal

from feedback.services.scoring import (
    DETRACTOR,
    PASSIVE,
    PROMOTER,
    classify,
    compute_mean,
    score,
)


def test_mean_basic():
    assert compute_mean(2, 3, 2) == Decimal("2.33")
    assert compute_mean(5, 5, 5) == Decimal("5.00")
    assert compute_mean(1, 1, 1) == Decimal("1.00")


def test_exact_three_is_passive():
    assert compute_mean(3, 3, 3) == Decimal("3.00")
    assert classify(Decimal("3.00")) == PASSIVE


def test_below_three_is_detractor():
    mean, cls = score(2, 3, 2)
    assert mean == Decimal("2.33")
    assert cls == DETRACTOR


def test_above_three_is_promoter():
    mean, cls = score(4, 5, 4)
    assert cls == PROMOTER
    assert mean > Decimal("3.00")


def test_boundaries():
    assert classify(compute_mean(3, 3, 2)) == DETRACTOR  # 2.67
    assert classify(compute_mean(4, 3, 3)) == PROMOTER  # 3.33
    assert classify(compute_mean(2, 4, 3)) == PASSIVE  # 3.00
