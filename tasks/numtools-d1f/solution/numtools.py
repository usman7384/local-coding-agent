"""Small numeric helpers: clamping, step rounding, ranks and windows."""

import math


def clamp(value, low, high):
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))


def round_to_step(value, step, mode="nearest"):
    """Round to a multiple of step; 'nearest' rounds halves upward."""
    if step <= 0:
        raise ValueError("step must be positive")
    units = value / step
    if mode == "down":
        whole = math.floor(units)
    elif mode == "up":
        whole = math.ceil(units)
    elif mode == "nearest":
        whole = math.floor(units + 0.5)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return whole * step


def _rank_index(count, fraction):
    rank = math.ceil(fraction * count)
    return clamp(rank, 1, count) - 1


def percentile(values, pct):
    """Nearest-rank percentile of a non-empty sequence, pct in [0, 100]."""
    if not values:
        raise ValueError("no values")
    if not 0 <= pct <= 100:
        raise ValueError("pct out of range")
    ordered = sorted(values)
    return ordered[_rank_index(len(ordered), pct / 100)]


def moving_average(values, window):
    if window < 1:
        raise ValueError("window must be positive")
    averages = []
    total = 0
    for index, value in enumerate(values):
        total += value
        if index >= window:
            total -= values[index - window]
        if index >= window - 1:
            averages.append(total / window)
    return averages


def rescale(value, src_low, src_high, dst_low, dst_high):
    span = src_high - src_low
    if span == 0:
        raise ValueError("empty source range")
    ratio = (value - src_low) / span
    return dst_low + ratio * (dst_high - dst_low)
