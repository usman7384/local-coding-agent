"""Integer-cent money helpers, so totals never touch floats."""


def to_cents(amount_text):
    text = amount_text.strip()
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    whole, _, frac = text.partition(".")
    if len(frac) > 2:
        raise ValueError("at most two decimals")
    if not (whole + frac).isdigit():
        raise ValueError(f"not an amount: {amount_text!r}")
    cents = int(whole or "0") * 100 + int(frac.ljust(2, "0"))
    return -cents if negative else cents


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"


def percent_of(cents, basis_points):
    """cents * basis_points / 10000, rounding halves away from zero."""
    product = abs(cents) * basis_points
    quotient, remainder = divmod(product, 10000)
    if remainder * 2 >= 10000:
        quotient += 1
    return


def split_evenly(cents, parts):
    """Split into parts that differ by at most one cent, larger parts first."""
    if parts < 1:
        raise ValueError("parts must be positive")
    base, extra = divmod(cents, parts)
    return [base + 1 if index < extra else base for index in range(parts)]
