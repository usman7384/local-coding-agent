from numtools import clamp, moving_average, percentile, round_to_step


def test_clamp_limits():
    """Clamping 15 to the range 0..10 should give 10, and -3 should give 0."""
    assert clamp(15, 0, 10) == 10
    assert clamp(-3, 0, 10) == 0


def test_round_to_nearest_step():
    """Rounding 7 to the nearest multiple of 5 should give 5, and 8 should give 10."""
    assert round_to_step(7, 5) == 5
    assert round_to_step(8, 5) == 10


def test_median_by_nearest_rank():
    """The middle value by nearest rank (50%) of [5, 1, 4, 2, 3] should be 3."""
    assert percentile([5, 1, 4, 2, 3], 50) == 3


def test_moving_average_pairs():
    """A window-2 moving average of [2, 4, 6, 8] should be [3.0, 5.0, 7.0]."""
    assert moving_average([2, 4, 6, 8], 2) == [3.0, 5.0, 7.0]
