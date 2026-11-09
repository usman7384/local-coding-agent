"""Line lexer for a small INI-like settings format."""

COMMENT_CHARS = "#;"
QUOTES = "\"'"


def strip_comment(line):
    in_quote = None
    for index, ch in enumerate(line):
        if in_quote:
            if ch == in_quote:
                in_quote = None
        elif ch in QUOTES:
            in_quote = ch
        elif ch in COMMENT_CHARS:
            return in_quote[:index]
    return line


def unquote(value):
    """Return (text, was_quoted) for a raw value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTES:
        return value[1:-1], True
    return value, False


def classify(raw_line):
    """Return (kind, payload) for one line: blank, section or pair."""
    line = strip_comment(raw_line).strip()
    if not line:
        return ("blank", None)
    if line.startswith("[") and line.endswith("]"):
        name = line[1:-1].strip().lower()
        if not name:
            raise ValueError("empty section name")
        return ("section", name)
    if "=" not in line:
        raise ValueError(f"expected key = value, got {line!r}")
    key, value = line.split("=", 1)
    key = key.strip().lower()
    if not key:
        raise ValueError("missing key")
    text, quoted = unquote(value.strip())
    return ("pair", (key, text, quoted))
