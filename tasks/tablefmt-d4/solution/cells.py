"""Turn raw values into cell text."""


def truncate(text, width):
    if len(text) <= width:
        return text
    return text[:width - 1] + "…"


def is_number(value):
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def format_number(value, decimals):
    return f"{value:.{decimals}f}"


def one_line(text):
    return " ".join(text.split())


def cell_text(value, decimals=2, max_width=20):
    if value is None:
        return ""
    if is_number(value):
        return format_number(value, decimals)
    return truncate(one_line(str(value)), max_width)
