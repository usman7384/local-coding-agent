"""Make bug-fixing tasks from the correct projects in corpus/. This is mutation testing: no model is involved.

    python make_tasks.py --per-project 5

For each project: break one line in one of the ways listed in BUGS, and keep the break only if the tests catch
it. Then add tasks until the project has `--per-project` of them. Existing tasks are never changed.
"""

import argparse
import itertools
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from utils import docstrings, functions, syntax_error

# Bugs people really write: (text, what it becomes). Each line can also be deleted.
BUGS = [(" <= ", " < "), (" < ", " <= "), (" >= ", " > "), (" > ", " >= "), (" == ", " != "), (" != ", " == "),
        (" + 1", " - 1"), (" - 1", " + 1"), (" + ", " - "), (" - ", " + "), ("+=", "-="), ("-=", "+="),
        (" and ", " or "), (" or ", " and "), ("min(", "max("), ("max(", "min("), ("[0]", "[-1]"), ("[-1]", "[0]")]
PROMPT = """Bug report

Something in this small Python project is broken. Behavior that users rely on no longer works as documented:

{expected}
Right now the project does not meet these expectations. Find the bug in the source code under src/ and fix it. Do not modify the tests.

Reproduce with:
  python -m pytest -q tests/test_visible.py
"""


def candidates(project: Path, meta: dict) -> list[dict]:
    """Every one-line bug inside a function the project's tests reach. D1: a function the tests call. D2: a helper."""
    found = []
    for file in meta["files"]:
        lines = (project / "src" / file).read_text(encoding="utf-8").split("\n")
        for name, first, last in functions("\n".join(lines)):
            level = "d1" if name in meta["entries"] else "d2" if name in meta["helpers"] else None
            for i in range(first, last) if level else []:                        # body lines, not the def line
                changed = [lines[i].replace(a, b, 1) for a, b in BUGS if a in lines[i]] + [None]  # None = deleted
                found += [{"file": file, "line": i, "level": level, "new": new} for new in changed]
    return found


def broken(project: Path, meta: dict, bugs: list[dict]) -> dict:
    """The project's files with these bugs applied."""
    files = {f: (project / "src" / f).read_text(encoding="utf-8").split("\n") for f in meta["files"]}
    for bug in bugs:
        files[bug["file"]][bug["line"]] = bug["new"]
    return {f: "\n".join(line for line in lines if line is not None) for f, lines in files.items()}


def failing(project: Path, files: dict) -> list[str] | None:
    """Names of the failing tests (visible and hidden), or None if the code does not run cleanly or hangs."""
    work = Path(tempfile.mkdtemp(prefix="mutant-"))
    for name, text in files.items():
        (work / "src").mkdir(exist_ok=True)
        (work / "src" / name).write_text(text, encoding="utf-8")
    (work / "tests").mkdir()
    for name in ("test_visible.py", "test_hidden.py"):
        shutil.copyfile(project / name, work / "tests" / name)
    (work / "pytest.ini").write_text("[pytest]\npythonpath = src\n")
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider", "tests"],
                             cwd=work, capture_output=True, text=True, timeout=20).stdout
    except subprocess.TimeoutExpired:                                         # an endless loop is not a fair task
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return re.findall(r"FAILED tests/(test_\w+)\.py::(\w+)", out)


def caught(project: Path, files: dict) -> list[str] | None:
    """The failing visible tests if the tests catch the bug fairly: some visible and some hidden tests fail,
    but not every visible test (otherwise the report says nothing). None otherwise."""
    if any(syntax_error(text) for text in files.values()):
        return None
    fails = failing(project, files) or []
    visible = [name for kind, name in fails if kind == "test_visible"]
    total = len(docstrings((project / "test_visible.py").read_text(encoding="utf-8")))
    hidden = [name for kind, name in fails if kind == "test_hidden"]
    return visible if visible and hidden and len(visible) < total else None


def write_task(tasks: Path, name: str, project: Path, meta: dict, bugs: list[dict], visible_fails: list[str]) -> None:
    """One task folder: the buggy repo, the hidden tests, the correct files and the bug report."""
    task = tasks / name
    for file, text in broken(project, meta, bugs).items():
        (task / "repo" / "src").mkdir(parents=True, exist_ok=True)
        (task / "repo" / "src" / file).write_text(text, encoding="utf-8", newline="\n")
    (task / "repo" / "tests").mkdir()
    (task / "hidden").mkdir()
    (task / "solution").mkdir()
    shutil.copyfile(project / "test_visible.py", task / "repo" / "tests" / "test_visible.py")
    shutil.copyfile(project / "test_hidden.py", task / "hidden" / "test_hidden.py")
    (task / "repo" / "pytest.ini").write_text("[pytest]\npythonpath = src\n", newline="\n")
    for file in {bug["file"] for bug in bugs}:
        shutil.copyfile(project / "src" / file, task / "solution" / file)
    docs = docstrings((project / "test_visible.py").read_text(encoding="utf-8"))
    expected = "".join(f"  Expected: {docs[test]}\n" for test in visible_fails)
    (task / "prompt.txt").write_text(PROMPT.format(expected=expected), encoding="utf-8", newline="\n")


parser = argparse.ArgumentParser()
parser.add_argument("--per-project", type=int, default=5)
parser.add_argument("--seed", type=int, default=7)
args = parser.parse_args()
tasks = Path("tasks")

for project in sorted(Path("corpus").iterdir()):
    meta = json.loads((project / "meta.json").read_text(encoding="utf-8"))
    existing = [t for t in tasks.iterdir() if t.name.rsplit("-", 1)[0] == project.name]
    taken = {(f.name, f.read_text(encoding="utf-8")) for t in existing for f in (t / "repo" / "src").iterdir()}
    want_d3 = 1 if len(meta["files"]) == 2 else 0                            # two-file projects get one more D3
    need = args.per_project - len(existing)
    pool = candidates(project, meta)
    random.Random(f"{args.seed}:{project.name}").shuffle(pool)                # same seed -> same tasks

    good, used_lines = [], set()                                              # bugs the tests catch, one per line
    for bug in pool:
        files = broken(project, meta, [bug])
        if len(good) >= 3 * need or (bug["file"], bug["line"]) in used_lines or (bug["file"], files[bug["file"]]) in taken:
            continue
        fails = caught(project, files)
        if fails:
            good.append((bug, fails))
            used_lines.add((bug["file"], bug["line"]))

    # Alternate D2 and D1 so each project gets both kinds, then add the two-file D3 task.
    d1, d2 = ([g for g in good if g[0]["level"] == level] for level in ("d1", "d2"))
    chosen = [([b], f) for b, f in (g for pair in itertools.zip_longest(d2, d1) for g in pair if g)][:need - want_d3]
    left = [b for b, _ in good if not any(b in bugs for bugs, _ in chosen)]   # bugs not used by a task yet
    pairs = ([a, b] for a, b in itertools.combinations(left, 2) if a["file"] != b["file"])
    d3 = next(((p, f) for p in pairs if (f := caught(project, broken(project, meta, p)))), None)  # first one caught
    chosen += [d3] if d3 and want_d3 else []

    for bugs, fails in chosen:
        level = "d3" if len(bugs) == 2 else bugs[0]["level"]
        name = next(n for n in (f"{project.name}-{level}{s}" for s in ["", "b", "c", "d", "e"]) if not (tasks / n).exists())
        write_task(tasks, name, project, meta, bugs, fails)
        print(name, [(b["file"], b["line"] + 1, b["new"]) for b in bugs], flush=True)
