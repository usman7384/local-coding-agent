import pytest

from timespan import format_span, parse_span


def test_hours_and_minutes():
    """A span written as '1h30m' should be 5400 seconds."""
    assert parse_span("1h30m") == 5400


def test_bare_number_is_seconds():
    """A bare number with no unit, such as '45', should mean 45 seconds."""
    assert parse_span("45") == 45


def test_format_keeps_two_largest_units():
    """Formatting 3725 seconds should give '1h2m': the two largest units, remainder dropped."""
    assert format_span(3725) == "1h2m"


def test_repeated_unit_rejected():
    """A span that repeats a unit, such as '5m5m', should be rejected with ValueError."""
    with pytest.raises(ValueError):
        parse_span("5m5m")
