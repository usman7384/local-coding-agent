"""Small helpers used by the harness. Nothing in here decides what the agent does; it just keeps the main files short."""

import ast
import contextlib
import difflib
import inspect
import itertools
import json
import random
import re
import shutil
import subprocess
import urllib.request
from collections import defaultdict
from math import comb
from pathlib import Path


def shorten(text: str, limit: int) -> str:
    """Keep the start and the end of a long text, cut the middle."""
    half = limit // 2
    return text if len(text) <= limit else f"{text[:half]}\n[... {len(text) - limit} characters cut ...]\n{text[-half:]}"


def steady(text: str) -> str:
    """Remove output that changes between identical runs (test timings, memory addresses), so equal runs stay equal."""
    return re.sub(r"0x[0-9a-f]{6,}", "0x...", re.sub(r" in \d+\.\d+s", "", text))


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


def project_file(workdir: Path, name: str) -> Path | None:
    """The existing file `name` inside `workdir`, or None if it is missing or points outside the project."""
    file = (workdir / name).resolve()
    return file if file.is_relative_to(workdir.resolve()) and file.is_file() else None


def syntax_error(source: str) -> str | None:
    """The first Python syntax error in `source` as "message on line N", or None if it parses."""
    try:
        compile(source, "<edit>", "exec")
    except (SyntaxError, ValueError) as error:
        return f"{getattr(error, 'msg', error)} on line {getattr(error, 'lineno', '?')}"
    return None


def same_file(a: Path, b: Path) -> bool:
    """True if both files exist and have identical bytes."""
    return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()


SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".notes.md"}  # never code


def changed(before: Path, after: Path) -> list[str]:
    """The files (relative paths) that differ between two folders."""
    names = set().union(*({p.relative_to(root).as_posix() for p in root.rglob("*")
                           if p.is_file() and not SKIP & set(p.relative_to(root).parts)} for root in (before, after)))
    return [name for name in sorted(names) if not same_file(before / name, after / name)]


def copy_back(names: list[str], source: Path, target: Path) -> None:
    """Make these files in `target` match `source`: copy them over, or delete the ones `source` lacks."""
    for name in names:
        if (source / name).exists():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target / name)
        else:
            (target / name).unlink(missing_ok=True)


def diff_dirs(before: Path, after: Path) -> str:
    """A unified diff of every file that differs between two folders."""
    read = lambda p: p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if p.exists() else []  # noqa: E731
    return "".join(line for name in changed(before, after)
                   for line in difflib.unified_diff(read(before / name), read(after / name), f"a/{name}", f"b/{name}"))


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


def get_json(url: str, default):
    """GET a URL and parse its JSON answer, or return `default` if the server does not offer it."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.load(response)
    except OSError:
        return default


def provenance(model: str, server: str) -> dict:
    """Which code, model and server produced a result, so every number can be traced back to them."""
    git = lambda *args: subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()  # noqa: E731
    dirty = "-dirty" if git("status", "--porcelain", "--", "*.py", "*.txt") else ""  # uncommitted code changes
    ollama = server.removesuffix("/v1")                                  # Ollama's own API sits next to /v1
    digests = {m["name"]: m["digest"][:12] for m in get_json(ollama + "/api/tags", {"models": []})["models"]}
    return {"commit": git("rev-parse", "--short", "HEAD") + dirty, "model": model,
            "model_digest": digests.get(model, digests.get(model + ":latest", "unknown")),
            "ollama": get_json(ollama + "/api/version", {"version": "unknown"})["version"]}


def functions(source: str) -> list[tuple[str, int, int]]:
    """(name, first line, last line) of every function and method in `source`; methods are named Class.method."""
    found = []
    for node in ast.parse(source).body:
        prefix, inner = (node.name + ".", node.body) if isinstance(node, ast.ClassDef) else ("", [node])
        found += [(prefix + f.name, f.lineno, f.end_lineno) for f in inner if isinstance(f, ast.FunctionDef)]
    return found


def local_names(lines: list[str]) -> list[str]:
    """The parameters (except self) and assigned names of one function (its def line first), for wrong-variable bugs."""
    params = re.findall(r"[(,]\s*\*{0,2}(\w+)", lines[0].split("->")[0])
    assigned = [m for line in lines[1:] for m in re.findall(r"^\s*(\w+)\s*[-+*/]?=(?!=)|\bfor (\w+) in", line)]
    return sorted({n for n in params + [a or b for a, b in assigned] if n not in ("self", "cls", "_")})


def docstrings(test_source: str) -> dict[str, str]:
    """test name -> its docstring, for every test function in a test file."""
    return {f.name: ast.get_docstring(f) or "" for f in ast.parse(test_source).body
            if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")}


def tool_spec(tool) -> dict:
    """A tool's JSON schema for the chat API, from its name, docstring and typed arguments (after `workdir`).
    MCP tools bring their own (`.spec`)."""
    if hasattr(tool, "spec"):
        return tool.spec
    args = list(inspect.signature(tool).parameters.values())[1:]
    kinds = {str: "string", int: "integer"}
    return {"type": "function", "function": {
        "name": tool.__name__, "description": inspect.getdoc(tool),
        "parameters": {"type": "object", "properties": {a.name: {"type": kinds[a.annotation]} for a in args},
                       "required": [a.name for a in args if a.default is a.empty]}}}


def call_tool(tools: dict, workdir: Path, call: dict, hooks: list = ()) -> tuple[str, dict, str]:
    """Run one tool call: (name, arguments, result). A call that does not fit any tool runs nothing ("malformed");
    a hook may refuse a call, and its message becomes the result."""
    name, raw = call["function"]["name"], call["function"].get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
        inspect.signature(tools[name]).bind(workdir, **args)               # the arguments fit the function
    except (KeyError, TypeError, ValueError):
        note = f"Nothing was run: {name}({raw}) is not a valid call. The tools are: {', '.join(tools)}."
        return "malformed", {"tool": name, "arguments": raw}, note
    refusal = next(filter(None, (hook(name, args) for hook in hooks)), None)
    return name, args, refusal or tools[name](workdir, **args)


@contextlib.contextmanager
def mcp_session(command: list[str]):
    """Start an MCP server (stdio: JSON-RPC 2.0, one message per line) and yield its tools as local functions."""
    server = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    ids = itertools.count(1)

    def rpc(method: str, params: dict, request: bool = True):
        """Send a request (or a notification: no id, no answer) and return its result."""
        server.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                                       **({"id": next(ids)} if request else {})}) + "\n")
        server.stdin.flush()
        return json.loads(server.stdout.readline())["result"] if request else None

    def proxy(tool: dict):
        """A local stand-in for a server tool: its name and schema; calls go to the server."""
        def forward(workdir: Path, **args) -> str:
            return rpc("tools/call", {"name": tool["name"], "arguments": args})["content"][0]["text"]
        forward.__name__, forward.spec = tool["name"], {"type": "function", "function": {
            "name": tool["name"], "description": tool.get("description", ""), "parameters": tool["inputSchema"]}}
        return forward

    try:
        rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "agent", "version": "1"}})
        rpc("notifications/initialized", {}, request=False)
        yield [proxy(tool) for tool in rpc("tools/list", {})["tools"]]
    finally:
        server.stdin.close()                                                 # end of input stops the server
        server.wait(timeout=30)


def transient(error: Exception) -> bool:
    """Worth retrying? Timeouts, lost connections, 429 and 5xx: yes. Other HTTP errors (bad request, key): no."""
    code = getattr(error, "code", None)
    return code is None or code == 429 or code >= 500


def mask(turn: list[dict]) -> list[dict]:
    """Observation masking: an old turn keeps its reply and calls; each result shrinks to its first line and failures."""
    return [{**m, "content": "\n".join(filter(None, [m["content"].split("\n")[0], fingerprint(m["content"]),
                                                     "[older result shortened]"]))} if m["role"] == "tool" else m
            for m in turn]


def repeated(trace: list[dict], times: int = 3) -> bool:
    """Were the last `times` tool calls the same call?"""
    calls = {json.dumps([s["action"], s.get("args")], sort_keys=True) for s in trace[-times:]}
    return len(trace) >= times and len(calls) == 1


def next_step(trace: list[dict]) -> int:
    """The next step number; steps keep counting across tries and samples."""
    return trace[-1]["step"] + 1 if trace else 1


def harness_step(trace: list[dict], action: str, result: str = "") -> dict:
    """A trace entry for the harness's own steps (RETRY, SAMPLE): no model call."""
    return {"step": next_step(trace), "action": action, "result": result, "tokens_in": 0, "tokens_out": 0}


def restore(original: Path, code: Path) -> None:
    """Put the original code back for a fresh sample (installed packages stay)."""
    copy_back(changed(original, code), original, code)


def sub_agent(step: int, action: str, result: str, steps: list[dict]) -> dict:
    """One trace entry for a sub-agent's run: its answer, its steps, their tokens."""
    return {"step": step, "action": action, "result": result, "steps": steps,
            "tokens_in": sum(s["tokens_in"] for s in steps), "tokens_out": sum(s["tokens_out"] for s in steps)}


def fingerprint(output: str) -> str | None:
    """The failing tests and their error lines in pytest output, or None if nothing failed."""
    return "\n".join(sorted(set(re.findall(r"(?m)^(?:FAILED|ERROR|E ) .*", output)))) or None


def stalls(trace: list[dict]) -> int:
    """How many test runs in a trace failed exactly like the failing run before them: steps that made no progress."""
    marks = [mark for s in trace if s["action"].lower() == "bash" and (mark := fingerprint(s["result"]))]
    return sum(a == b for a, b in zip(marks, marks[1:]))


def lesson(attempt: int, diff: str, check: str, rejected: str = "") -> str:
    """A lesson from a failed try, for the next one: what it changed in src/, and how the visible tests still fail
    or, if they passed, why the critic rejected the change."""
    change = (f"It changed src/ like this, and the files still contain that change:\n{shorten(diff, 800)}" if diff
              else "It left src/ unchanged: its edits failed or were undone.")
    why = (f"The visible tests pass, but a reviewer rejected the change:\n{shorten(rejected, 600)}" if rejected
           else f"The visible tests still fail with:\n{shorten(fingerprint(check) or check, 600)}")
    return (f"\n\nLesson from failed try {attempt} (its conversation is gone): {change}\n{why}\n"
            "Do not repeat what it tried. Find the real cause and fix it.")
