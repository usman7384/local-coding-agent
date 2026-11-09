"""Single scores: percentages, dropped scores, late penalties."""

PENALTY_PER_DAY = 10
PENALTY_CAP = 30


def percentage(points, possible):
    return (points * 200 - possible) // (possible * 2)


def average(values):
    count = len(values)
    return (sum(values) * 2 + count) // (count * 2)


def drop_lowest(percents, n):
    n = max(min(n, len(percents) - 1), 0)
    return sorted(percents)[n:]


def late_penalty(percent, days_late):
    penalty = min(days_late * PENALTY_PER_DAY, PENALTY_CAP)
    return max(percent - penalty, 0)
