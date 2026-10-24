"""Small helpers used by the harness. Nothing in here is about agents; it just keeps the main files short."""

import difflib
import json
import random
from collections import defaultdict
from math import comb
from pathlib import Path


def shorten(text: str, limit: int) -> str:
    """Keep the start and the end of a long text, cut the middle."""
    half = limit // 2
    return text if len(text) <= limit else f"{text[:half]}\n[... {len(text) - limit} characters cut ...]\n{text[-half:]}"


def match_indentation(content: str, old: str, new: str) -> tuple[str, str, str]:
    """If `old` matches exactly one place in `content` when leading spaces are ignored,
    return the file's real lines, `new` shifted by the same indentation, and a note."""
    lines, old_lines = content.split("\n"), old.split("\n")
    wanted = [line.strip() for line in old_lines]                       # compare lines without indentation
    starts = [i for i in range(len(lines) - len(old_lines) + 1)
              if [line.strip() for line in lines[i:i + len(old_lines)]] == wanted]
    if len(starts) != 1:                                                # no match, or ambiguous: give up
        return old, new, ""
    found = lines[starts[0]:starts[0] + len(old_lines)]                 # the real lines in the file
    indent = lambda line: len(line) - len(line.lstrip(" "))  # noqa: E731
    shift = indent(found[0]) - indent(old_lines[0])                     # how far off the model was
    new_lines = [" " * shift + line if shift >= 0 else line[min(-shift, indent(line)):] for line in new.split("\n")]
    return "\n".join(found), "\n".join(new_lines), " (indentation adjusted)"


def same_file(a: Path, b: Path) -> bool:
    """True if both files exist and have identical bytes."""
    return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()


def diff_dirs(before: Path, after: Path) -> str:
    """Unified diff of every .py file in `before` against the same file in `after`."""
    read = lambda p: p.read_text(encoding="utf-8").splitlines(keepends=True) if p.exists() else []  # noqa: E731
    return "".join(line for f in sorted(before.glob("*.py"))
                   for line in difflib.unified_diff(read(f), read(after / f.name), f"a/{f.name}", f"b/{f.name}"))


def read_jsonl(path: Path) -> list[dict]:
    """One JSON object per line -> list of dicts (empty if the file does not exist yet)."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def append_jsonl(path: Path, row: dict) -> None:
    """Add one JSON object as a new line."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def by_task(rows: list[dict]) -> dict[str, list[bool]]:
    """Group attempt results by task: {"ringlog-d1": [True, False, ...], ...}, one entry per repeat."""
    passes = defaultdict(list)
    for row in rows:
        passes[row["task"]].append(row["passed"])
    return dict(passes)


def pass_at_k(c: int, n: int, k: int) -> float:
    """Chance that at least one of k tries passes, given c passes out of n tries (unbiased estimate)."""
    return 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(c: int, n: int, k: int) -> float:
    """pass^k: chance that ALL k tries pass, given c passes out of n tries (unbiased estimate)."""
    return comb(c, k) / comb(n, k)


def bootstrap(items: list, stat, rounds: int = 10_000, seed: int = 0) -> tuple[float, float]:
    """95% confidence interval of stat(items): recompute it on `rounds` random resamples of the items."""
    rng = random.Random(seed)                                               # fixed seed -> same interval every time
    values = sorted(stat(rng.choices(items, k=len(items))) for _ in range(rounds))
    return values[int(0.025 * rounds)], values[int(0.975 * rounds)]          # the middle 95%
