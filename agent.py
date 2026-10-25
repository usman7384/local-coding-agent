"""A minimal coding agent.

Each step: send the conversation to the model, take ONE action from its reply, run it with the matching
tool (see tools.py), and add the result to the conversation. The model writes its action in a fenced block,
for example:

    ```
    VIEW: src/ringlog.py
    ```

and finishes with a block containing only DONE.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from tools import TOOLS

MODEL = os.environ.get("LLM_MODEL", "arh-qwen2.5-coder-7b-8k")
URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1") + "/chat/completions"
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8")

MAX_STEPS = 20        # the agent gets at most 20 model replies
KEEP_MESSAGES = 10    # the model sees the system prompt, the bug report and only the last 10 messages


def ask_model(messages: list[dict], seed: int) -> str:
    """One call to the local model through its OpenAI-compatible chat API."""
    body = {"model": MODEL, "messages": messages, "seed": seed, "temperature": 0.7, "top_p": 0.9, "max_tokens": 768}
    request = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)["choices"][0]["message"]["content"]


def parse_action(reply: str) -> tuple[str, str]:
    """Return (kind, text) of the single action block in the reply, or ("MALFORMED", "")."""
    blocks = [b.strip() for b in re.findall(r"```[^\n]*\n(.*?)```", reply, re.S)]       # every fenced block
    actions = [b for b in blocks if b == "DONE" or b.split(":")[0] in TOOLS]          # blocks naming a tool
    kind, _, text = actions[0].partition(":") if len(actions) == 1 else ("MALFORMED", "", "")
    return kind, text.strip()


def run_agent(bug_report: str, workdir: Path, seed: int) -> list[dict]:
    """Let the model work on `workdir` until it says DONE or runs out of steps. Returns the step-by-step trace."""
    history, trace = [], []
    for step in range(1, MAX_STEPS + 1):
        messages = [{"role": "system", "content": SYSTEM_PROMPT},           # how to behave
                    {"role": "user", "content": bug_report}] + history[-KEEP_MESSAGES:]  # the task + recent steps
        reply = ask_model(messages, seed=seed * 100 + step)                 # same seed -> same sampling
        kind, text = parse_action(reply)
        if kind == "DONE":
            return trace + [{"step": step, "reply": reply, "action": "DONE"}]
        result = TOOLS[kind](workdir, text)                                 # run the chosen tool
        trace.append({"step": step, "reply": reply, "action": kind, "result": result})
        # Small models copy their own past replies, so a malformed one is not kept in the history.
        shown = reply if kind != "MALFORMED" else "(malformed reply removed)"
        history += [{"role": "assistant", "content": shown}, {"role": "user", "content": result}]
    return trace
