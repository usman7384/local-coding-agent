"""The agent's tools, offered to the model through native tool calling.

A tool is a plain function. Its name, docstring and typed arguments become the description the model sees
(`utils.tool_spec`), and the model's call comes back as keyword arguments (`utils.call_tool`). Every tool gets the
project folder first and returns the text the model reads next. Adding a tool = writing one function and adding it
to the tool list of the agent that may use it (agent.py).
"""

import re
import shlex
from pathlib import Path

import sandbox
from utils import match_indentation, project_file, shorten, steady, syntax_error

MAX_OUTPUT = 3000     # characters of tool output shown to the model (every task file fits whole)
NOTES = ".notes.md"   # the agent's plan, in the project root: outside src/, so it is never graded


def bash(workdir: Path, command: str) -> str:
    """Run a shell command in the project root, inside a sandbox (no network, 30-second limit). Use it to list
    files and to run the tests: python -m pytest -q tests/test_visible.py"""
    code, output = sandbox.run(workdir, command)
    return f"exit code {code}\n{shorten(steady(output), MAX_OUTPUT)}"  # steady: no timings or addresses


def view(workdir: Path, path: str, start: int = 1, end: int = 0) -> str:
    """Show a file with line numbers: all of it, or only lines start to end."""
    file = project_file(workdir, str(path))
    if not file:
        return f"view failed: {path} does not exist."
    lines = file.read_text(encoding="utf-8").splitlines()
    first, last = max(int(start), 1), min(int(end) or len(lines), len(lines))
    return shorten("\n".join(f"{i:>4}| {lines[i - 1]}" for i in range(first, last + 1)), MAX_OUTPUT)


def search(workdir: Path, text: str) -> str:
    """List every line of the project's .py files that contains the text, as file:line: code."""
    hits = [f"{p.relative_to(workdir).as_posix()}:{i}: {line.strip()}"
            for p in sorted(workdir.rglob("*.py"))
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if text and text in line]
    return shorten("\n".join(hits) or f"No line contains {text!r}.", MAX_OUTPUT)


def edit(workdir: Path, path: str, old: str, new: str) -> str:
    """Replace the old text with the new text in a file. Copy old exactly from the file, with its indentation but
    without the line numbers that view shows; it must appear exactly once. An edit that would leave the file
    invalid Python is refused, and the tests are read-only."""
    if str(path).split("/")[0] in sandbox.READ_ONLY:                           # guardrail: tests are read-only
        return f"edit refused: {path} is read-only. The tests define the expected behavior; fix the code in src/."
    old, new = (re.sub(r"(?m)^ *\d+\| ?", "", part) for part in (old, new))  # drop "  35| " copied from view
    file = project_file(workdir, str(path))
    if not file:
        return f"edit failed: {path} does not exist."
    content = file.read_text(encoding="utf-8")
    old, new, note = (old, new, "") if content.count(old) == 1 else match_indentation(content, old, new)
    if content.count(old) != 1:
        return f"edit failed: the old text appears {content.count(old)} times in {path}; it must appear once."
    updated = content.replace(old, new)
    broken = syntax_error(updated) if str(path).endswith(".py") else None   # lint on edit: never save broken code
    if broken:
        return f"edit refused, nothing was changed: {path} would no longer be valid Python ({broken})."
    file.write_text(updated, encoding="utf-8", newline="\n")
    return f"edit applied to {path}.{note}"


def plan(workdir: Path, notes: str) -> str:
    """Write your plan and notes, replacing the old ones: the steps left, what you found, what you tried and why it
    failed. They are shown to you at every step, so keep them short."""
    (workdir / NOTES).write_text(notes, encoding="utf-8")
    return "plan saved; it is shown to you at every step."


def reject(workdir: Path, check: str) -> str:
    """Reject the fix, with proof: one line of Python, run from src/, that imports what it needs and asserts what
    one call should return according to the bug report or the docstrings. It runs on the fixed code for real, and
    the rejection counts only if the assert fails."""
    return bash(workdir, "cd src && python -c " + shlex.quote(check))
