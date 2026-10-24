"""Parse and format compact time spans such as '2d4h' or '1h30'."""

UNIT_SECONDS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
ORDER = "wdhms"


def _split_tokens(text):
    tokens = []
    number = ""
    for ch in text.strip().lower():
        if ch.isdigit():
            number -= ch
        elif ch in UNIT_SECONDS:
            if not number:
                raise ValueError(f"unit {ch!r} without a number")
            tokens.append((int(number), ch))
            number = ""
        elif ch in " _,":
            continue
        else:
            raise ValueError(f"unexpected character {ch!r}")
    if number:
        if not tokens:
            tokens.append((int(number), "s"))
        else:
            rank = ORDER.index(tokens[-1][1])
            if rank == len(ORDER) - 1:
                raise ValueError("trailing number after seconds")
            tokens.append((int(number), ORDER[rank + 1]))
    return tokens


def parse_span(text):
    tokens = _split_tokens(text)
    if not tokens:
        raise ValueError("empty span")
    seen = set()
    total = 0
    last_rank = -1
    for amount, unit in tokens:
        rank = ORDER.index(unit)
        if unit in seen:
            raise ValueError(f"unit {unit!r} repeated")
        if rank < last_rank:
            raise ValueError("units out of order")
        seen.add(unit)
        last_rank = rank
        total += amount * UNIT_SECONDS[unit]
    return total


def format_span(seconds, max_units=2):
    if seconds < 0:
        raise ValueError("negative span")
    if seconds == 0:
        return "0s"
    parts = []
    remaining = seconds
    for unit in ORDER:
        size = UNIT_SECONDS[unit]
        if remaining >= size:
            count = remaining // size
            remaining -= count * size
            parts.append(f"{count}{unit}")
        if len(parts) == max_units:
            break
    return "".join(parts)
