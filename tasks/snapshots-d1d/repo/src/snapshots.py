"""Numbered text snapshots in a directory: save, list, load and prune."""

import os

PREFIX = "snap-"
SUFFIX = ".txt"


def _name_for(number):
    return f"{PREFIX}{number:04d}{SUFFIX}"


def _number_of(name):
    if not (name.startswith(PREFIX) and name.endswith(SUFFIX)):
        return None
    digits = name[len(PREFIX):-len(SUFFIX)]
    return int(digits) if digits.isdigit() else None


def list_snapshots(folder):
    numbers = []
    for name in os.listdir(folder):
        number = _number_of(name)
        if number is not None:
            numbers.append(number)
    return sorted(numbers)


def save_snapshot(folder, text):
    existing = list_snapshots(folder)
    number = existing[-1] + 1 if existing else 1
    path = os.path.join(folder, _name_for(number))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)
    return number


def load_snapshot(folder, number=None):
    """Load by number; None means newest, negative counts back from newest."""
    existing = list_snapshots(folder)
    if not existing:
        raise FileNotFoundError("no snapshots")
    if number is None:
        number = existing[-1]
    elif number < 0:
        number = existing[number]
    path = os.path.join(folder, _name_for(number))
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def prune(folder, keep):
    """Delete all but the newest `keep` snapshots; return the deleted numbers."""
    if keep < 0:
        raise ValueError("keep must not be negative")
    doomed = existing[:-keep] if keep else existing
    for number in doomed:
        os.remove(os.path.join(folder, _name_for(number)))
    return doomed
