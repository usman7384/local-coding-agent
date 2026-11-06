"""A minimal coding agent.

Each step: send the conversation to the model, take ONE action from its reply, run it with the matching
tool (see tools.py), and add the result to the conversation. The model writes its action in a fenced block,
for example:

    ```
    VIEW: src/ringlog.py
    ```

and finishes with a block containing only DONE. The harness then runs the visible tests itself (verify); if they
fail, the agent gets one more try with a fresh conversation and a lesson from the failed one.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from grade import PYTEST
from tools import TOOLS, bash, view
from utils import diff_dirs, lesson, project_file

MODEL = os.environ.get("LLM_MODEL", "arh-qwen2.5-coder-7b-8k")
SERVER = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
URL = SERVER + "/chat/completions"
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8")

MAX_STEPS = 20        # each try gets at most 20 model replies
TRIES = 2             # verify: if the visible tests fail after a try, one more try with a lesson
KEEP_MESSAGES = 10    # the model sees the system prompt, the bug report and only the last 10 messages
OPEN_FILES = 2        # the files it viewed or edited most recently are always shown, fresh from disk


def ask_model(messages: list[dict], seed: int) -> tuple[str, dict]:
    """One call to the local model through its OpenAI-compatible chat API. Returns the reply and its token counts."""
    body = {"model": MODEL, "messages": messages, "seed": seed, "temperature": 0.7, "top_p": 0.9, "max_tokens": 768}
    request = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        answer = json.load(response)
    usage = answer["usage"]                                             # tokens read and written by this call
    return answer["choices"][0]["message"]["content"], {"tokens_in": usage["prompt_tokens"],
                                                        "tokens_out": usage["completion_tokens"]}


def parse_action(reply: str) -> tuple[str, str]:
    """Return (kind, text) of the single action block in the reply, or ("MALFORMED", "")."""
    blocks = [b.strip() for b in re.findall(r"```[^\n]*\n(.*?)```", reply, re.S)]       # every fenced block
    actions = [b for b in blocks if b == "DONE" or b.split(":")[0] in TOOLS]          # blocks naming a tool
    kind, _, text = actions[0].partition(":") if len(actions) == 1 else ("MALFORMED", "", "")
    return kind, text.strip()


def run_agent(bug_report: str, workdir: Path, seed: int, original: Path) -> list[dict]:
    """Up to TRIES tries at the bug. After each, verify with the visible tests; if they fail, start a fresh
    conversation whose bug report carries a lesson: what the failed try changed and how the tests still fail."""
    trace, lessons = [], ""
    for attempt in range(1, TRIES + 1):
        trace += one_try(bug_report + lessons, workdir, seed, first=len(trace) + 1)
        check = bash(workdir, PYTEST + "tests/test_visible.py")            # verify: do not take DONE on trust
        if check.startswith("exit code 0") or attempt == TRIES:
            return trace
        lessons += lesson(attempt, diff_dirs(original, workdir / "src"), check)  # kept; the old conversation is not
        trace.append({"step": len(trace) + 1, "action": "RETRY", "result": lessons, "tokens_in": 0, "tokens_out": 0})


def one_try(bug_report: str, workdir: Path, seed: int, first: int) -> list[dict]:
    """Let the model work on `workdir` until it says DONE or runs out of steps. Returns the step-by-step trace."""
    history, trace, opened = [], [], []
    for step in range(first, first + MAX_STEPS):
        # "Open files" panel: the real, current content of the files being worked on, so nothing is edited from memory.
        files = "\n\n".join(f"{name}\n{view(workdir, name)}" for name in opened)
        panel = [{"role": "user", "content": f"Current content of the files you are working on:\n\n{files}"}] if opened else []
        messages = [{"role": "system", "content": SYSTEM_PROMPT},           # how to behave
                    {"role": "user", "content": bug_report}] + history[-KEEP_MESSAGES:] + panel  # task, recent steps, files
        reply, tokens = ask_model(messages, seed=seed * 100 + step)         # same seed -> same sampling
        kind, text = parse_action(reply)
        if kind == "DONE":
            return trace + [{"step": step, "reply": reply, "action": "DONE", **tokens}]
        result = TOOLS[kind](workdir, text)                                 # run the chosen tool
        trace.append({"step": step, "reply": reply, "action": kind, "result": result, **tokens})
        name = text.split()[0] if kind in ("VIEW", "EDIT") and text else ""     # the file this action touched
        opened = ([f for f in opened if f != name] + [name])[-OPEN_FILES:] if project_file(workdir, name) else opened
        # Small models copy their own past replies, so a malformed one is not kept in the history.
        shown = reply if kind != "MALFORMED" else "(malformed reply removed)"
        history += [{"role": "assistant", "content": shown}, {"role": "user", "content": result}]
    return trace
