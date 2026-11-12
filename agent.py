"""A coding agent: a model calling tools in a loop.

Each step sends the conversation and the tool list to the model through its chat API (native tool calling). The
model answers with tool calls, which run (tools.py) and go back into the conversation, or with plain text, which
ends the try. Then the harness runs the visible tests itself (verify); if they fail, one more try starts with a
fresh conversation and a lesson from the failed one.

Sub-agents are the same loop with their own prompt and tools. Every component beyond the core loop is a switch,
off by default (the README lists them all), for example:
- AGENT_EXPLORER=1: before the first try, a read-only explorer (view, search) says where the bug is.
- AGENT_CRITIC=1:   after a try whose tests pass, a critic reads the fix and may reject it with an assert that runs.
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
API_KEY = os.environ.get("LLM_API_KEY", "")                               # for hosted APIs; never recorded
PRICES = [float(os.environ.get(f"LLM_PRICE_{kind}", "0")) for kind in ("IN", "OUT")]  # USD per million tokens
# Reasoning models think before they answer. LLM_THINK="none" (the default) turns that off, and models that do not
# think ignore it; "" sends nothing. Thinking tokens count against MAX_TOKENS, so a thinking run needs a larger one.
THINK = os.environ.get("LLM_THINK", "none")
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "768"))
EXPLORER = os.environ.get("AGENT_EXPLORER") == "1"
CRITIC = os.environ.get("AGENT_CRITIC") == "1"
PLAN = os.environ.get("AGENT_PLAN") == "1"              # a plan tool; the plan is shown at every step
COMPACT = os.environ.get("AGENT_COMPACT") == "1"        # older turns stay in view, their results shrunk
SAMPLES = int(os.environ.get("AGENT_SAMPLES", "1"))     # best-of-N: independent samples until one passes verify
MCP = os.environ.get("AGENT_MCP") == "1"                # the fixer's tools come from an MCP server (run.py starts it)
GUARDRAILS = os.environ.get("AGENT_GUARDRAILS") == "1"  # refuse risky commands, stop a try that repeats one call
BUDGET = int(os.environ.get("AGENT_BUDGET", "0"))       # tokens per try (0: no budget)
MEMORY = os.environ.get("AGENT_MEMORY", "")             # a lessons file from learn.py, added to the bug report
SWITCHES = {"explorer": EXPLORER, "critic": CRITIC, "plan": PLAN, "compact": COMPACT, "samples": SAMPLES, "mcp": MCP,
            "guardrails": GUARDRAILS, "budget": BUDGET, "memory": MEMORY}    # recorded with every result

MAX_STEPS = 20        # each try gets at most 20 model replies
TRIES = 2             # verify: if the visible tests fail after a try, one more try with a lesson
KEEP_TURNS = 5        # the model sees the system prompt, the bug report and only its last 5 turns (reply + results)
OPEN_FILES = 2        # the files it viewed or edited most recently are always shown, fresh from disk
EXPLORER_STEPS = 6    # the explorer gets at most 6 replies to point at the bug

FIXER_TOOLS = [bash, view, search, edit] + ([plan] if PLAN else [])
EXPLORER_TOOLS = [view, search]                # read-only: the explorer cannot change anything
CRITIC_TOOLS = [reject]                        # the critic accepts by answering in text, or calls reject
PROMPTS = {name: (Path(__file__).parent / "prompts" / f"{name}.txt").read_text(encoding="utf-8")
           for name in ("fixer", "explorer", "critic", "learner")}     # how each agent should behave
HOOKS = [guard] if GUARDRAILS else []          # run before every tool call; each may refuse it


def ask_model(messages: list[dict], tools: list, seed: int) -> tuple[dict, dict]:
    """One call to the model through its OpenAI-compatible chat API (the gateway: any server, an API key, retries
    with backoff on transient failures). Returns its message and the token counts."""
    body = {"model": MODEL, "messages": messages, "seed": seed, "temperature": 0.7, "top_p": 0.9,
            "max_tokens": MAX_TOKENS, **({"tools": [tool_spec(t) for t in tools]} if tools else {}),
            **({"reasoning_effort": THINK} if THINK else {})}                 # thinking: only when set
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})}
    request = urllib.request.Request(URL, json.dumps(body).encode(), headers)
    for wait in (2, 8, 30, None):                                           # 3 retries: rate limits, server errors
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                answer = json.load(response)
            break
        except (urllib.error.URLError, TimeoutError) as error:
            if wait is None or not transient(error):                       # a bad request will not get better
                raise
            time.sleep(wait)
    usage = answer["usage"]                                                 # tokens read and written by this call
    return answer["choices"][0]["message"], {"tokens_in": usage["prompt_tokens"], "tokens_out": usage["completion_tokens"]}


def run_agent(bug_report: str, workdir: Path, seed: int, original: Path, tools: list = FIXER_TOOLS) -> list[dict]:
    """Up to SAMPLES independent samples (best-of-N), each from the original code, until one is accepted. A sample is
    up to TRIES tries, each verified by the visible tests (and, with the critic on, a review). After a failed try the
    next starts with a fresh conversation whose bug report carries a lesson: what the failed try changed, and how
    the tests failed or why the critic rejected it."""
    trace = [explore(bug_report, workdir, seed + 1)] if EXPLORER else []          # step 0: where is the bug?
    if trace and trace[0]["result"]:
        bug_report += (f"\n\nA read-only explorer looked at the code first. Its guess: {trace[0]['result']}\n"
                       "Check it yourself before you edit.")
    if MEMORY:                                                                  # opt-in memory across tasks
        bug_report += f"\n\nLessons from earlier runs (general advice):\n{Path(MEMORY).read_text(encoding='utf-8')}"
    for sample in range(SAMPLES):
        if sample:                                         # best-of-N: the next sample starts from the original code
            restore(original, workdir / "src")
            (workdir / NOTES).unlink(missing_ok=True)
            trace.append(harness_step(trace, "SAMPLE"))
        lessons = ""
        for attempt in range(1, TRIES + 1):                # steps keep counting, so every try samples differently
            trace += loop(PROMPTS["fixer"], bug_report + lessons, workdir, tools, seed, next_step(trace))
            check = bash(workdir, PYTEST + "tests/test_visible.py")            # verify: do not take "done" on trust
            green, diff = check.startswith("exit code 0"), diff_dirs(original, workdir / "src")
            if green and CRITIC and attempt < TRIES:                            # green tests: the critic reads the fix
                trace.append(critique(bug_report, workdir, diff, seed + 2, next_step(trace)))
            rejected = trace[-1]["result"] if trace[-1]["action"] == "REVIEW" and trace[-1]["result"] != "ACCEPT" else ""
            if green and not rejected:
                return trace
            if attempt < TRIES:
                lessons += lesson(attempt, diff, check, rejected)              # kept; the old conversation is not
                trace.append(harness_step(trace, "RETRY", lessons))
    return trace


def loop(system: str, task: str, workdir: Path, tools: list, seed: int, first: int, max_steps: int = MAX_STEPS) -> list[dict]:
    """The agent loop: the model calls tools until it answers without one ("done"), runs out of steps, or a guardrail
    stops it. Returns the trace, one entry per tool call, each timed (a span); a reply's text, tokens and model
    latency go with its first call."""
    tools, turns, trace, opened, spent = {t.__name__: t for t in tools}, [], [], [], 0
    for step in range(first, first + max_steps):
        # "Open files" panel: the real, current content of the files being worked on, so nothing is edited from memory.
        files = "\n\n".join(f"{name}\n{view(workdir, name)}" for name in opened)
        notes = (workdir / NOTES).read_text(encoding="utf-8") if "plan" in tools and (workdir / NOTES).exists() else ""
        panel = (f"Your plan and notes:\n{notes}\n\n" if notes else "") + (
            f"Current content of the files you are working on:\n\n{files}" if opened else "")
        older = [mask(turn) for turn in turns[:-KEEP_TURNS]] if COMPACT else []   # compaction: shrunk, not dropped
        messages = [{"role": "system", "content": system},                      # how to behave
                    {"role": "user", "content": task}] + sum(older + turns[-KEEP_TURNS:], []) + (  # task, turns,
                   [{"role": "user", "content": panel}] if panel else [])                        # plan and files
        started = time.time()
        message, tokens = ask_model(messages, list(tools.values()), seed=seed * 100 + step)  # same seed, same sampling
        usage = {**tokens, "model_ms": round(1000 * (time.time() - started))}   # span: tokens and latency of the call
        reply, calls = message.get("content") or "", message.get("tool_calls") or []
        if not calls:
            return trace + [{"step": step, "reply": reply, "action": "done", **usage}]
        turn = [{"role": "assistant", "content": reply, "tool_calls": calls}]
        for i, call in enumerate(calls):                                    # a reply may call several tools
            started = time.time()
            name, args, result = call_tool(tools, workdir, call, HOOKS)
            trace.append({"step": step, "reply": "" if i else reply, "action": name, "args": args, "result": result,
                          "tool_ms": round(1000 * (time.time() - started)), **(dict.fromkeys(usage, 0) if i else usage)})
            turn.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": result})
            path = str(args.get("path", "")) if name in ("view", "edit") else ""   # the file this call touched
            opened = ([f for f in opened if f != path] + [path])[-OPEN_FILES:] if project_file(workdir, path) else opened
        turns.append(turn)                                                  # a turn = the reply and its results
        spent += tokens["tokens_in"] + tokens["tokens_out"]
        stops = {"the token budget is spent": BUDGET and spent > BUDGET,           # guardrails that end a try early
                 "the same call 3 times in a row": GUARDRAILS and repeated(trace)}
        stop = next((why for why, hit in stops.items() if hit), None)
        if stop:
            return trace + [{"step": step, "action": "STOP", "result": stop, "tokens_in": 0, "tokens_out": 0}]
    return trace


def explore(bug_report: str, workdir: Path, seed: int) -> dict:
    """The explorer: a sub-agent with a fresh conversation and read-only tools. It sees the bug report and the failing
    visible tests and answers with where the bug is. Its steps stay inside one EXPLORE entry."""
    tests = bash(workdir, PYTEST + "tests/test_visible.py")
    steps = loop(PROMPTS["explorer"], f"{bug_report}\n\nThe visible tests now:\n{tests}", workdir, EXPLORER_TOOLS, seed,
                 first=1, max_steps=EXPLORER_STEPS)
    guess = steps[-1]["reply"].strip() if steps[-1]["action"] == "done" else ""   # no answer within its steps: none
    return sub_agent(0, "EXPLORE", guess, steps)


def critique(bug_report: str, workdir: Path, diff: str, seed: int, step: int) -> dict:
    """The critic: one reply from a sub-agent that reads the bug report and the fix. It accepts by answering in text,
    or rejects by calling reject with a one-line assert. A model cannot run code in its head, so a rejection counts
    only if that assert really fails on the fixed code."""
    names = re.findall(r"(?m)^\+\+\+ b/(\S+)", diff)                         # the files the fix changed
    files = "\n\n".join(f"src/{name}\n{view(workdir, 'src/' + name)}" for name in names)
    steps = loop(PROMPTS["critic"], f"{bug_report}\n\nThe fix:\n{diff}\n\nThe changed files now:\n\n{files}", workdir,
                 CRITIC_TOOLS, seed, first=1, max_steps=1)
    proof = next((s for s in steps if s["action"] == "reject" and "AssertionError" in s["result"]), None)
    return sub_agent(step, "REVIEW", f"REJECT: {proof['args']['check']}\n{proof['result']}" if proof else "ACCEPT", steps)
