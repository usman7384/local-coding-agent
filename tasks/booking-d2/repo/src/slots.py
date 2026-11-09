"""Half-open time intervals in minutes since midnight."""


def parse_time(text):
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def format_time(minutes):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def overlaps(first, second):
    return first[0] < second[1] and second[0] < first[1]


def merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def gaps(busy, start, end):
    """Free stretches between start and end that are not covered by busy."""
    free = []
    for b_start, b_end in merge(busy):
        if b_start > cursor:
            free.append((cursor, min(b_start, end)))
        cursor = max(cursor, b_end)
    if cursor < end:
        free.append((cursor, end))
    return free
