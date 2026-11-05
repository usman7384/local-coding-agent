"""Business-day and calendar-month arithmetic on datetime.date values."""

from datetime import date, timedelta

WEEKEND = {5, 6}


def is_workday(day, holidays=()):
    return day.weekday() not in WEEKEND and day not in holidays


def add_workdays(start, count, holidays=()):
    """Move count workdays forward (or backward when negative) from start."""
    step = 1 if count >= 0 else -1
    remaining = abs(count)
    current = start
    while remaining > 0:
        current += timedelta(days=step)
        if is_workday(current, holidays):
            remaining -= 1
    return current


def workdays_between(start, end, holidays=()):
    """Count workdays in the half-open range [start, end)."""
    if end < start:
        return -workdays_between(end, start, holidays)
    count = 0
    current = start
    while current < end:
        if is_workday(current, holidays):
            count += 1
        current += timedelta(days=1)
    return count


def _days_in_month(year, month):
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def add_months(day, months):
    """Shift by whole months, pinning to the last day of shorter months."""
    index = day.year * 12 + (day.month - 1) + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    last = _days_in_month(year, month)
    return date(year, month, min(day.day, last))
