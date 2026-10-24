"""A minimal coding agent.

Each step: send the conversation to the model, take ONE action from its reply, run it,
and add the result to the conversation. The model writes its action in a fenced block:

    BASH: <command>        run a shell command in the sandbox (tests, cat, ls, ...)
    EDIT: <file>           replace text in a file, written as
          <<<<<<< OLD
          exact old lines
          =======
          new lines
          >>>>>>> NEW
    DONE                   stop
"""

import json
import os
import re
import urllib.request
from pathlib import Path

import sandbox
from utils import match_indentation, shorten

MODEL = os.environ.get("LLM_MODEL", "arh-qwen2.5-coder-7b-8k")
URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1") + "/chat/completions"
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8")

MAX_STEPS = 20        # the agent gets at most 20 model replies
KEEP_MESSAGES = 10    # the model sees the system prompt, the bug report and only the last 10 messages
MAX_OUTPUT = 3000     # characters of command output shown to the model (every task file fits whole)
EDIT_FORMAT = re.compile(r"(\S+)\n<<<<<<< OLD\n(.*?)\n=======\n(.*?)\n?>>>>>>> NEW", re.S)


def ask_model(messages: list[dict], seed: int) -> str:
    """One call to the local model through its OpenAI-compatible chat API."""
    body = {"model": MODEL, "messages": messages, "seed": seed, "temperature": 0.7, "top_p": 0.9, "max_tokens": 768}
    request = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)["choices"][0]["message"]["content"]


def parse_action(reply: str) -> tuple[str, str]:
    """Return (kind, text) of the single action block in the reply, or ("MALFORMED", "")."""
    blocks = [b.strip() for b in re.findall(r"```[^\n]*\n(.*?)```", reply, re.S)]       # every fenced block
    actions = [b for b in blocks if b == "DONE" or b.startswith(("BASH:", "EDIT:"))]  # only the action blocks
    kind, _, text = actions[0].partition(":") if len(actions) == 1 else ("MALFORMED", "", "")
    return kind, text.strip()


def bash(workdir: Path, command: str) -> str:
    """Tool: run a shell command in the sandbox and show its exit code and (shortened) output."""
    code, output = sandbox.run(workdir, command)
    return f"exit code {code}\n{shorten(output, MAX_OUTPUT)}"


def edit(workdir: Path, text: str) -> str:
    """Tool: replace the OLD text with the NEW text in a file. OLD must appear exactly once."""
    match = EDIT_FORMAT.fullmatch(text)
    if not match:
        return "EDIT failed: write the file name, then <<<<<<< OLD, =======, >>>>>>> NEW lines."
    name, old, new = match.groups()
    file = (workdir / name).resolve()
    if not file.is_relative_to(workdir.resolve()) or not file.is_file():  # stay inside the project folder
        return f"EDIT failed: {name} does not exist."
    content = file.read_text(encoding="utf-8")
    old, new, note = (old, new, "") if content.count(old) == 1 else match_indentation(content, old, new)
    if content.count(old) != 1:
        return f"EDIT failed: the OLD text appears {content.count(old)} times in {name}; it must appear once."
    file.write_text(content.replace(old, new), encoding="utf-8", newline="\n")
    return f"EDIT applied to {name}.{note}"


# What each action does. Every tool gets the project folder and the action's text and returns what the model sees.
TOOLS = {
    "BASH": bash,
    "EDIT": edit,
    "MALFORMED": lambda workdir, text: "Nothing was run. Reply with exactly one fenced block: BASH:, EDIT: or DONE.",
}


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
