"""Load settings text into per-section dictionaries with typed values."""

from lexer import classify

TRUE_WORDS = {"yes", "on", "true"}
FALSE_WORDS = {"no", "off", "false"}


def coerce(value):
    lowered = value.lower()
    if lowered in TRUE_WORDS:
        return True
    if lowered in FALSE_WORDS:
        return False
    digits = value[1:] if value.startswith("-") else value
    if digits.isdigit():
        return int(value)
    return value


def load(text, defaults=None):
    result = {"main": dict(defaults or {})}
    section = "main"
    seen = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        try:
            kind, payload = classify(raw)
        except ValueError as exc:
            raise ValueError(f"line {number}: {exc}") from None
        if kind == "section":
            section = payload
            result.setdefault(section, {})
        elif kind == "pair":
            key, value, quoted = payload
            if (section, key) in seen:
                raise ValueError(f"line {number}: duplicate key {key!r}")
            seen.add((section, key))
            result[section][key] = value if quoted else coerce(value)
    return result


def get_path(settings, dotted, fallback=None):
    section, _, key = dotted.rpartition(".")
    section = section.lower() or "main"
    return settings.get(section, {}).get(key.lower(), fallback)
