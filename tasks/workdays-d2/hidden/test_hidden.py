from datetime import date

from workdays import add_months, add_workdays, is_workday, workdays_between


def test_backwards_over_weekend():
    assert add_workdays(date(2024, 3, 11), -1) == date(2024, 3, 8)
    assert add_workdays(date(2024, 3, 13), -3) == date(2024, 3, 8)


def test_zero_count_returns_start_even_on_weekend():
    saturday = date(2024, 3, 9)
    assert add_workdays(saturday, 0) == saturday


def test_weekend_start_moves_to_monday():
    assert add_workdays(date(2024, 3, 9), 1) == date(2024, 3, 11)


def test_reversed_range_is_negative():
    assert workdays_between(date(2024, 3, 11), date(2024, 3, 4)) == -5
    assert workdays_between(date(2024, 3, 6), date(2024, 3, 6)) == 0


def test_range_with_holiday_and_weekend():
    holidays = {date(2024, 12, 25)}
    assert workdays_between(date(2024, 12, 23), date(2024, 12, 30), holidays) == 4


def test_is_workday_flags():
    assert is_workday(date(2024, 3, 8))
    assert not is_workday(date(2024, 3, 10))
    assert not is_workday(date(2024, 3, 8), {date(2024, 3, 8)})


def test_leap_february():
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_backwards_and_across_years():
    assert add_months(date(2024, 3, 31), -1) == date(2024, 2, 29)
    assert add_months(date(2023, 12, 15), 1) == date(2024, 1, 15)
    assert add_months(date(2024, 1, 10), -13) == date(2022, 12, 10)


def test_december_and_long_months_unchanged():
    assert add_months(date(2024, 11, 30), 1) == date(2024, 12, 30)
    assert add_months(date(2024, 10, 31), 2) == date(2024, 12, 31)
