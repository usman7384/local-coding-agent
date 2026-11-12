"""A coding agent: a model calling tools in a loop.

Each step sends the conversation and the tool list to the model (native tool calling). Tool calls run (tools.py)
and their results go back into the conversation; a reply without a tool call ends the try. The harness then runs
the visible tests itself (verify) and, if they fail, gives one more try with a lesson. Sub-agents are the same
loop with their own prompt and tools. Every component beyond this core is a switch, off by default.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from grade import PYTEST
from tools import NOTES, bash, edit, guard, plan, reject, search, view
from utils import (call_tool, diff_dirs, harness_step, lesson, mask, next_step, project_file, repeated, restore,
                   sub_agent, tool_spec, transient)

MODEL = os.environ.get("LLM_MODEL", "arh-qwen3.5-4b-8k")
SERVER = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")      # any OpenAI-compatible chat API
URL = SERVER + "/chat/completions"
API_KEY = os.environ.get("LLM_API_KEY", "")                               # hosted APIs; never recorded
PRICES = [float(os.environ.get(f"LLM_PRICE_{kind}", "0")) for kind in ("IN", "OUT")]  # USD per million tokens
THINK = os.environ.get("LLM_THINK", "none")              # reasoning_effort; "none" = no thinking, "" = not sent
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "768"))  # thinking counts against it

EXPLORER = os.environ.get("AGENT_EXPLORER") == "1"      # a read-only sub-agent finds the bug first
CRITIC = os.environ.get("AGENT_CRITIC") == "1"          # a sub-agent may reject a green fix with an assert
PLAN = os.environ.get("AGENT_PLAN") == "1"              # a plan tool; the plan stays in view
COMPACT = os.environ.get("AGENT_COMPACT") == "1"        # old turns stay, their results shrunk
SAMPLES = int(os.environ.get("AGENT_SAMPLES", "1"))     # best-of-N: fresh samples until one passes verify
MCP = os.environ.get("AGENT_MCP") == "1"                # the fixer's tools come from an MCP server
GUARDRAILS = os.environ.get("AGENT_GUARDRAILS") == "1"  # refuse risky commands, stop repeated calls
BUDGET = int(os.environ.get("AGENT_BUDGET", "0"))       # tokens per try (0 = no limit)
MEMORY = os.environ.get("AGENT_MEMORY", "")             # a lessons file (learn.py) added to the bug report
SWITCHES = {"explorer": EXPLORER, "critic": CRITIC, "plan": PLAN, "compact": COMPACT, "samples": SAMPLES, "mcp": MCP,
            "guardrails": GUARDRAILS, "budget": BUDGET, "memory": MEMORY}    # recorded with every result

MAX_STEPS = 20        # model replies per try
TRIES = 2             # verify: one more try with a lesson if the visible tests fail
KEEP_TURNS = 5        # recent turns (reply + results) kept in full
OPEN_FILES = 2        # files shown fresh from disk at every step
EXPLORER_STEPS = 6    # replies the explorer gets

FIXER_TOOLS = [bash, view, search, edit] + ([plan] if PLAN else [])
EXPLORER_TOOLS = [view, search]                # read-only
CRITIC_TOOLS = [reject]                        # no call = accept
PROMPTS = {name: (Path(__file__).parent / "prompts" / f"{name}.txt").read_text(encoding="utf-8")
           for name in ("fixer", "explorer", "critic", "learner")}
HOOKS = [guard] if GUARDRAILS else []          # run before every tool call; may refuse it
TEST = PYTEST + "tests/test_visible.py"        # the benchmark's verify command; fix.py passes the project's own


def ask_model(messages: list[dict], tools: list, seed: int) -> tuple[dict, dict]:
    """One chat API call, retried with backoff on transient failures. Returns the message and its token counts."""
    body = {"model": MODEL, "messages": messages, "seed": seed, "temperature": 0.7, "top_p": 0.9,
            "max_tokens": MAX_TOKENS, **({"tools": [tool_spec(t) for t in tools]} if tools else {}),
            **({"reasoning_effort": THINK} if THINK else {})}
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})}
    request = urllib.request.Request(URL, json.dumps(body).encode(), headers)
    for wait in (2, 8, 30, None):                                           # 3 retries
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                answer = json.load(response)
            break
        except (urllib.error.URLError, TimeoutError) as error:
            if wait is None or not transient(error):
                raise
            time.sleep(wait)
    usage = answer["usage"]
    return answer["choices"][0]["message"], {"tokens_in": usage["prompt_tokens"], "tokens_out": usage["completion_tokens"]}


def run_agent(bug_report: str, workdir: Path, seed: int, original: Path, tools: list = FIXER_TOOLS,
              code: str = "src", test: str = TEST) -> list[dict]:
    """Up to SAMPLES fresh samples (best-of-N) of up to TRIES tries each, until a try passes verify (and the critic).
    A failed try's lesson goes into the next try's bug report; its conversation does not. `original` is the
    untouched copy of `workdir / code`; `test` is the command that verifies a fix."""
    trace = [explore(bug_report, workdir, seed + 1, test)] if EXPLORER else []
    if trace and trace[0]["result"]:
        bug_report += f"\n\nA read-only explorer's guess: {trace[0]['result']}\nCheck it yourself before you edit."
    if MEMORY:
        bug_report += f"\n\nLessons from earlier runs (general advice):\n{Path(MEMORY).read_text(encoding='utf-8')}"
    for sample in range(SAMPLES):
        if sample:                                                      # a fresh sample: the original code again
            restore(original, workdir / code)
            (workdir / NOTES).unlink(missing_ok=True)
            trace.append(harness_step(trace, "SAMPLE"))
        lessons = ""
        for attempt in range(1, TRIES + 1):                            # steps keep counting: new seeds each try
            trace += loop(PROMPTS["fixer"], bug_report + lessons, workdir, tools, seed, next_step(trace))
            check = bash(workdir, test)                                 # verify: "done" proves nothing
            green, diff = check.startswith("exit code 0"), diff_dirs(original, workdir / code)
            if green and CRITIC and attempt < TRIES:
                trace.append(critique(bug_report, workdir, diff, seed + 2, next_step(trace), code))
            rejected = trace[-1]["result"] if trace[-1]["action"] == "REVIEW" and trace[-1]["result"] != "ACCEPT" else ""
            if green and not rejected:
                return trace
            if attempt < TRIES:
                lessons += lesson(attempt, diff, check, rejected)
                trace.append(harness_step(trace, "RETRY", lessons))
    return trace


def loop(system: str, task: str, workdir: Path, tools: list, seed: int, first: int, max_steps: int = MAX_STEPS) -> list[dict]:
    """The agent loop: tool calls until a reply without one ("done"), the step limit, or a guardrail stop.
    Returns one timed trace entry per tool call; a reply's text, tokens and latency go with its first call."""
    tools, turns, trace, opened, spent = {t.__name__: t for t in tools}, [], [], [], 0
    for step in range(first, first + max_steps):
        files = "\n\n".join(f"{name}\n{view(workdir, name)}" for name in opened)    # fresh from disk, not memory
        notes = (workdir / NOTES).read_text(encoding="utf-8") if "plan" in tools and (workdir / NOTES).exists() else ""
        panel = (f"Your plan and notes:\n{notes}\n\n" if notes else "") + (
            f"Current content of the files you are working on:\n\n{files}" if opened else "")
        older = [mask(turn) for turn in turns[:-KEEP_TURNS]] if COMPACT else []   # compaction: shrink, not drop
        messages = ([{"role": "system", "content": system}, {"role": "user", "content": task}]
                    + sum(older + turns[-KEEP_TURNS:], []) + ([{"role": "user", "content": panel}] if panel else []))
        started = time.time()
        message, tokens = ask_model(messages, list(tools.values()), seed=seed * 100 + step)  # same seed, same sample
        usage = {**tokens, "model_ms": round(1000 * (time.time() - started))}
        reply, calls = message.get("content") or "", message.get("tool_calls") or []
        if not calls:
            return trace + [{"step": step, "reply": reply, "action": "done", **usage}]
        turn = [{"role": "assistant", "content": reply, "tool_calls": calls}]
        for i, call in enumerate(calls):                                # a reply may call several tools
            started = time.time()
            name, args, result = call_tool(tools, workdir, call, HOOKS)
            trace.append({"step": step, "reply": "" if i else reply, "action": name, "args": args, "result": result,
                          "tool_ms": round(1000 * (time.time() - started)), **(dict.fromkeys(usage, 0) if i else usage)})
            turn.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": result})
            path = str(args.get("path", "")) if name in ("view", "edit") else ""
            opened = ([f for f in opened if f != path] + [path])[-OPEN_FILES:] if project_file(workdir, path) else opened
        turns.append(turn)
        spent += tokens["tokens_in"] + tokens["tokens_out"]
        stops = {"the token budget is spent": BUDGET and spent > BUDGET,
                 "the same call 3 times in a row": GUARDRAILS and repeated(trace)}
        stop = next((why for why, hit in stops.items() if hit), None)
        if stop:
            return trace + [{"step": step, "action": "STOP", "result": stop, "tokens_in": 0, "tokens_out": 0}]
    return trace


def explore(bug_report: str, workdir: Path, seed: int, test: str = TEST) -> dict:
    """The explorer sub-agent: read-only tools, a fresh conversation, the failing tests; answers where the bug is."""
    tests = bash(workdir, test)
    steps = loop(PROMPTS["explorer"], f"{bug_report}\n\nThe visible tests now:\n{tests}", workdir, EXPLORER_TOOLS, seed,
                 first=1, max_steps=EXPLORER_STEPS)
    return sub_agent(0, "EXPLORE", steps[-1]["reply"].strip() if steps[-1]["action"] == "done" else "", steps)


def critique(bug_report: str, workdir: Path, diff: str, seed: int, step: int, code: str = "src") -> dict:
    """The critic sub-agent: one reply on the fix. A rejection counts only if its assert really fails."""
    paths = [(Path(code) / name).as_posix() for name in re.findall(r"(?m)^\+\+\+ b/(\S+)", diff)]  # changed files
    files = "\n\n".join(f"{path}\n{view(workdir, path)}" for path in paths)
    steps = loop(PROMPTS["critic"], f"{bug_report}\n\nThe fix:\n{diff}\n\nThe changed files now:\n\n{files}", workdir,
                 CRITIC_TOOLS, seed, first=1, max_steps=1)
    proof = next((s for s in steps if s["action"] == "reject" and "AssertionError" in s["result"]), None)
    return sub_agent(step, "REVIEW", f"REJECT: {proof['args']['check']}\n{proof['result']}" if proof else "ACCEPT", steps)
