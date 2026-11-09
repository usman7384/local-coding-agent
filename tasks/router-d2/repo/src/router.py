"""Match request paths to handler names and build paths back."""

from convert import format_value, parse_spec, take
from segments import encode, join_path, split_path


class MethodNotAllowed(Exception):
    pass


def step(spec, rest):
    if isinstance(spec, str):
        if rest[:1] != [spec]:
            raise ValueError("static mismatch")
    kind, name = spec
    value, used = take(kind, rest)
    return {name: value}, used, 0


def match_route(specs, rest):
    params = {}
    weights = []
    for spec in specs:
        try:
            found, used, weight = step(spec, rest)
        except ValueError:
            return None
        params.update(found)
        weights.append(weight)
        rest = rest[used:]
    if rest:
        return None
    return params, weights


def pick(found, method):
    found.sort(key=lambda item: item[0], reverse=True)
    for weights, name, params, methods in found:
        if method in methods:
            return name, params
    return None


def build(specs, params):
    parts = []
    for spec in specs:
        if isinstance(spec, str):
            parts.append(encode(spec))
        else:
            parts.append(format_value(spec[0], params[spec[1]]))
    return join_path(parts)


class Router:
    def __init__(self):
        self.routes = []

    def add(self, pattern, handler_name, methods=("GET",)):
        specs = [parse_spec(p) or p for p in split_path(pattern)]
        self.routes.append((specs, handler_name, tuple(methods)))

    def match(self, method, path):
        parts = split_path(path)
        found = []
        for specs, name, methods in self.routes:
            hit = match_route(specs, parts)
            if hit is not None:
                found.append((hit[1], name, hit[0], methods))
        if not found:
            raise LookupError("not found: " + path)
        result = pick(found, method)
        if result is None:
            raise MethodNotAllowed(method + " " + path)
        return result

    def url_for(self, handler_name, **params):
        for specs, name, _ in self.routes:
            if name == handler_name:
                return build(specs, params)
        raise LookupError("unknown handler: " + handler_name)
