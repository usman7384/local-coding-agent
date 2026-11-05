import pytest

from numtools import clamp, moving_average, percentile, rescale, round_to_step


def test_clamp_inverted_range_rejected():
    with pytest.raises(ValueError):
        clamp(1, 5, 2)


def test_halves_round_up():
    assert round_to_step(2.5, 1) == 3
    assert round_to_step(7.5, 5) == 10
    assert round_to_step(-2.5, 1) == -2


def test_directed_rounding():
    assert round_to_step(7, 5, "down") == 5
    assert round_to_step(6, 5, "up") == 10
    assert round_to_step(-7, 5, "down") == -10
    assert round_to_step(-7, 5, "up") == -5


def test_bad_step_or_mode():
    with pytest.raises(ValueError):
        round_to_step(1, 0)
    with pytest.raises(ValueError):
        round_to_step(1, 1, "sideways")


def test_percentile_extremes():
    data = [30, 10, 20]
    assert percentile(data, 0) == 10
    assert percentile(data, 100) == 30


def test_percentile_upper_ranks():
    data = list(range(1, 11))
    assert percentile(data, 90) == 9
    assert percentile(data, 91) == 10
    assert percentile(data, 25) == 3


def test_percentile_invalid():
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1], 101)


def test_moving_average_edges():
    assert moving_average([1, 2], 3) == []
    assert moving_average([4, 8, 6], 1) == [4.0, 8.0, 6.0]
    assert moving_average([3, 3, 9, 0], 3) == [5.0, 4.0]


def test_rescale():
    assert rescale(5, 0, 10, 0, 100) == 50
    assert rescale(0, -1, 1, 10, 20) == 15
    with pytest.raises(ValueError):
        rescale(1, 2, 2, 0, 1)
