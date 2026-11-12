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
    """A tool function as the chat API describes a tool: its name, its docstring, and its arguments after `workdir`
    (str -> string, int -> integer; arguments without a default are required). A tool served over MCP brings its
    own description (`.spec`)."""
    if hasattr(tool, "spec"):
        return tool.spec
    args = list(inspect.signature(tool).parameters.values())[1:]
    kinds = {str: "string", int: "integer"}
    return {"type": "function", "function": {
        "name": tool.__name__, "description": inspect.getdoc(tool),
        "parameters": {"type": "object", "properties": {a.name: {"type": kinds[a.annotation]} for a in args},
                       "required": [a.name for a in args if a.default is a.empty]}}}


def call_tool(tools: dict, workdir: Path, call: dict, hooks: list = ()) -> tuple[str, dict, str]:
    """Run one tool call from the model: (tool name, arguments, result). A call to an unknown tool, or with
    arguments that are not JSON or do not fit the tool, runs nothing and is returned as "malformed", with a result
    the model can read and correct. Every hook sees the call first and may refuse it (its message is the result)."""
    name, raw = call["function"]["name"], call["function"].get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
        inspect.signature(tools[name]).bind(workdir, **args)               # the arguments fit the function
    except (KeyError, TypeError, ValueError):
        note = f"Nothing was run: {name}({raw}) is not a valid call. The tools are: {', '.join(tools)}."
        return "malformed", {"tool": name, "arguments": raw}, note
    refusal = next(filter(None, (hook(name, args) for hook in hooks)), None)   # pre-call hooks, e.g. guardrails
    return name, args, refusal or tools[name](workdir, **args)


@contextlib.contextmanager
def mcp_session(command: list[str]):
    """Start an MCP server (stdio transport: JSON-RPC 2.0, one message per line), discover its tools, and yield them
    as functions the agent loop can call, each with the server's own description as `.spec`. Stops it afterwards."""
    server = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    ids = itertools.count(1)

    def rpc(method: str, params: dict, request: bool = True):
        """Send a request (or a notification, which gets no answer) and return its result."""
        server.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                                       **({"id": next(ids)} if request else {})}) + "\n")
        server.stdin.flush()
        return json.loads(server.stdout.readline())["result"] if request else None

    def proxy(tool: dict):
        """A local stand-in for one server tool: same name, the server's schema, calls forwarded to the server."""
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
        server.stdin.close()                                                 # the server stops at the end of input
        server.wait(timeout=30)


def transient(error: Exception) -> bool:
    """Is a failed model call worth retrying? Yes for timeouts, lost connections, rate limits (429) and server
    errors (5xx); no for other HTTP errors, such as a bad request or a wrong API key."""
    code = getattr(error, "code", None)                                      # only HTTP errors have a status code
    return code is None or code == 429 or code >= 500


def mask(turn: list[dict]) -> list[dict]:
    """Observation masking for an old turn: the model's reply and calls stay, and each tool result shrinks to its
    first line plus the failing tests it showed, so old decisions stay in view at a fraction of the tokens."""
    return [{**m, "content": "\n".join(filter(None, [m["content"].split("\n")[0], fingerprint(m["content"]),
                                                     "[older result shortened]"]))} if m["role"] == "tool" else m
            for m in turn]


def next_step(trace: list[dict]) -> int:
    """The number of the next step in a trace. Steps keep counting across tries, so every try samples differently."""
    return trace[-1]["step"] + 1 if trace else 1


def harness_step(trace: list[dict], action: str, result: str = "") -> dict:
    """A trace entry for a step the harness takes itself (RETRY, SAMPLE): no model call, no tokens."""
    return {"step": next_step(trace), "action": action, "result": result, "tokens_in": 0, "tokens_out": 0}


def restore(original: Path, src: Path) -> None:
    """Put the original code back, so a new sample starts from the buggy project, not from another sample's edits."""
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(original, src)


def sub_agent(step: int, action: str, result: str, steps: list[dict]) -> dict:
    """One trace entry for a sub-agent's whole run: its verdict, its own steps, and the tokens they used."""
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
