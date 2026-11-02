"""Tests for inbound SMS reply parsing."""

from feedback.services.sms import parse_three_digit_reply


def test_spaced_digits():
    assert parse_three_digit_reply("4 5 4") == (4, 5, 4)


def test_joined_digits():
    assert parse_three_digit_reply("454") == (4, 5, 4)


def test_with_noise():
    assert parse_three_digit_reply("my rating: 3-2-5 thanks") == (3, 2, 5)


def test_rejects_wrong_count():
    assert parse_three_digit_reply("4 5") is None
    assert parse_three_digit_reply("4 5 4 5") is None


def test_rejects_out_of_range_only():
    assert parse_three_digit_reply("6 7 8") is None
    assert parse_three_digit_reply("") is None
