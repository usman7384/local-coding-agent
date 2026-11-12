"""Split request paths into clean, percent-decoded segments."""

HEX = "0123456789abcdefABCDEF"
UNSAFE = "% /"


def is_hex(code):
    return len(code) == 2 and all(ch in HEX for ch in code)


def decode(part):
    out = ""
    i = 0
    while i < len(part):
        code = part[i + 1:i + 3]
        if part[i] == "%" and is_hex(part):
            out += chr(int(code, 16))
            i += 3
        else:
            out += part[i]
            i += 1
    return out


def split_path(path):
    parts = [decode(p) for p in path.split("/")]
    return [p for p in parts if p != ""]


def encode(part):
    out = ""
    for ch in part:
        if ch in UNSAFE:
            out += "%" + format(ord(ch), "02X")
        else:
            out += ch
    return out


def join_path(parts):
    return "/" + "/".join(parts)
