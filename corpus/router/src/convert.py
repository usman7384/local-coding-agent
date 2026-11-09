"""Typed route parameters such as <int:id>, <str:name> and <path:rest>."""

from segments import encode


def to_int(text):
    if not text.isdigit():
        raise ValueError("not an integer: " + text)
    return int(text)


def to_str(text):
    if text == "":
        raise ValueError("empty segment")
    return text


CONVERTERS = {"int": to_int, "str": to_str}


def parse_spec(token):
    if not (token.startswith("<") and token.endswith(">")):
        return None
    kind, _, name = token[1:-1].partition(":")
    if name == "":
        return ("str", kind)
    if kind != "path" and kind not in CONVERTERS:
        raise ValueError("unknown type: " + kind)
    return (kind, name)


def take(kind, parts):
    if not parts:
        raise ValueError("no segment left")
    if kind == "path":
        return "/".join(parts), len(parts)
    return CONVERTERS[kind](parts[0]), 1


def format_value(kind, value):
    text = str(value)
    if kind == "path":
        return "/".join(encode(p) for p in text.split("/"))
    return encode(text)
