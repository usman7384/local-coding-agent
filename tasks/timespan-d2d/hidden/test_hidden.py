import pytest

from timespan import format_span, parse_span


def test_trailing_number_takes_next_unit():
    assert parse_span("1h30") == 5400
    assert parse_span("2d3") == 2 * 86400 + 3 * 3600


def test_weeks_and_separators():
    assert parse_span("2w") == 2 * 604800
    assert parse_span("1d 2h") == 93600
    assert parse_span("1_000s") == 1000


def test_out_of_order_rejected():
    with pytest.raises(ValueError):
        parse_span("5m1h")


def test_trailing_number_after_seconds_rejected():
    with pytest.raises(ValueError):
        parse_span("10s5")


def test_bad_inputs_rejected():
    for text in ["", "   ", "3x", "h"]:
        with pytest.raises(ValueError):
            parse_span(text)


def test_format_zero_and_small():
    assert format_span(0) == "0s"
    assert format_span(59) == "59s"
    assert format_span(60) == "1m"


def test_format_skips_empty_units():
    assert format_span(3601) == "1h1s"
    assert format_span(604800 + 5) == "1w5s"


def test_format_more_units():
    assert format_span(90061, max_units=3) == "1d1h1m"
    assert format_span(90061, max_units=1) == "1d"


def test_format_negative_rejected():
    with pytest.raises(ValueError):
        format_span(-1)
