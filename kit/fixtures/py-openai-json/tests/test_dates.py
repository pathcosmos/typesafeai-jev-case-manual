from datetime import date

from app.dates import days_until, is_overdue


def test_days_until():
    assert days_until(date(2026, 10, 1), date(2026, 9, 25)) == 6


def test_overdue():
    assert is_overdue(date(2026, 9, 1), date(2026, 9, 25))
