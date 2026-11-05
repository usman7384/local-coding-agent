from datetime import date

from workdays import add_months, add_workdays, workdays_between


def test_friday_plus_one_is_monday():
    """One business day after Friday 2024-03-08 should be Monday 2024-03-11."""
    assert add_workdays(date(2024, 3, 8), 1) == date(2024, 3, 11)


def test_full_week_has_five_workdays():
    """From Monday 2024-03-04 up to (not including) the next Monday there should be 5 business days."""
    assert workdays_between(date(2024, 3, 4), date(2024, 3, 11)) == 5


def test_month_end_is_pinned():
    """Adding one month to 2023-01-31 should give 2023-02-28, the last day of February."""
    assert add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)


def test_holiday_is_skipped():
    """If Tuesday 2024-03-12 is a holiday, two business days after Monday 2024-03-11 should be Thursday 2024-03-14."""
    holidays = {date(2024, 3, 12)}
    assert add_workdays(date(2024, 3, 11), 2, holidays) == date(2024, 3, 14)
