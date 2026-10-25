"""The agent's tools. Each one gets the project folder and the text after "NAME:" and returns what the model sees.

    BASH: <command>            run a shell command in the Docker sandbox (tests, ls, ...)
    VIEW: <file> [10-30]       show a file (or some of its lines) with line numbers
    SEARCH: <text>             list every line containing the text, as file:line: code
    EDIT: <file>               replace text in a file, written as
          <<<<<<< OLD
          exact old lines
          =======
          new lines
          >>>>>>> NEW

Adding a tool = writing its function and adding one line to TOOLS at the bottom.
"""

import re
from pathlib import Path

import sandbox
from utils import match_indentation, project_file, shorten

MAX_OUTPUT = 3000     # characters of tool output shown to the model (every task file fits whole)
EDIT_FORMAT = re.compile(r"(\S+)\n<<<<<<< OLD\n(.*?)\n=======\n(.*?)\n?>>>>>>> NEW", re.S)


def bash(workdir: Path, command: str) -> str:
    """Run a shell command in the sandbox and show its exit code and (shortened) output."""
    code, output = sandbox.run(workdir, command)
    return f"exit code {code}\n{shorten(output, MAX_OUTPUT)}"


def view(workdir: Path, text: str) -> str:
    """Show a file with line numbers, all of it ("src/a.py") or a range ("src/a.py 10-30")."""
    match = re.fullmatch(r"(\S+)(?:\s+(\d+)-(\d+))?", text)
    file = project_file(workdir, match[1]) if match else None
    if not file:
        return "VIEW failed: write an existing file name, optionally followed by a line range like 10-30."
    lines = file.read_text(encoding="utf-8").splitlines()
    start, end = int(match[2] or 1), int(match[3] or len(lines))
    return shorten("\n".join(f"{i:>4}| {lines[i - 1]}" for i in range(max(start, 1), min(end, len(lines)) + 1)),
                   MAX_OUTPUT)


def search(workdir: Path, text: str) -> str:
    """Every line containing `text` in the project's .py files, as file:line: code."""
    hits = [f"{p.relative_to(workdir).as_posix()}:{i}: {line.strip()}"
            for p in sorted(workdir.rglob("*.py"))
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if text and text in line]
    return shorten("\n".join(hits) or f"No line contains {text!r}.", MAX_OUTPUT)


def edit(workdir: Path, text: str) -> str:
    """Replace the OLD text with the NEW text in a file. OLD must appear exactly once."""
    match = EDIT_FORMAT.fullmatch(text)
    if not match:
        return "EDIT failed: write the file name, then <<<<<<< OLD, =======, >>>>>>> NEW lines."
    name, old, new = match.groups()
    old, new = (re.sub(r"(?m)^ *\d+\| ?", "", part) for part in (old, new))  # drop "  35| " copied from VIEW
    file = project_file(workdir, name)
    if not file:
        return f"EDIT failed: {name} does not exist."
    content = file.read_text(encoding="utf-8")
    old, new, note = (old, new, "") if content.count(old) == 1 else match_indentation(content, old, new)
    if content.count(old) != 1:
        return f"EDIT failed: the OLD text appears {content.count(old)} times in {name}; it must appear once."
    file.write_text(content.replace(old, new), encoding="utf-8", newline="\n")
    return f"EDIT applied to {name}.{note}"


# Action name -> tool. The agent's parser accepts any name in this dict.
TOOLS = {
    "BASH": bash,
    "VIEW": view,
    "SEARCH": search,
    "EDIT": edit,
    "MALFORMED": lambda workdir, text: "Nothing was run. Reply with exactly one fenced block: "
                                       "BASH:, VIEW:, SEARCH:, EDIT: or DONE.",
}
