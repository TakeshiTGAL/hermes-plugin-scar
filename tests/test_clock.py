"""The weekday follows the stored offset, not UTC."""

from support import clock


def test_a_tokyo_morning_is_monday():
    text = clock.receipt(1, "2026-10-26T08:45:00+09:00")
    assert text == "scar #1, Monday 08:45 +09:00, you pressed deny"


def test_the_same_instant_in_utc_is_sunday():
    text = clock.receipt(1, "2026-10-25T23:45:00+00:00")
    assert text == "scar #1, Sunday 23:45 +00:00, you pressed deny"


def test_a_naive_clock_is_refused():
    import pytest

    with pytest.raises(ValueError):
        clock.parse_when("2026-10-26T08:45:00")
