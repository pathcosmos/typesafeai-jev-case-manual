"""마감일 계산 유틸리티."""
from datetime import date


def days_until(deadline: date, today: date) -> int:
    return (deadline - today).days


def is_overdue(deadline: date, today: date) -> bool:
    return days_until(deadline, today) < 0
