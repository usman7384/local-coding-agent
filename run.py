"""Run every task several times and save one result line per attempt.

    python run.py --run-id baseline --repeats 3
    python run.py --run-id smoke --repeats 1 --tasks ringlog-d1,timespan-d1
    python run.py --run-id my-change --tasks tasks/bench-45.txt     # only the first 45 tasks
    python run.py --run-id redteam --dir redteam                     # prompt-injection tasks
    python run.py --run-id fast --workers 4                          # attempts in parallel (an API model)

Finished attempts are skipped, so an interrupted run can simply be started again.
"""

import argparse
import contextlib
import json
import re
import shutil
import sys
import tempfile
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sandbox
from agent import FIXER_TOOLS, MAX_TOKENS, MCP, MODEL, PRICES, SERVER, SWITCHES, THINK, run_agent
from grade import grade
from utils import append_jsonl, diff_dirs, mcp_session, provenance, read_jsonl

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", default="baseline")
parser.add_argument("--repeats", type=int, default=3)
parser.add_argument("--tasks", help="comma-separated task ids, or a .txt file listing them (default: all)")
parser.add_argument("--dir", default="tasks", help="the task folder (tasks, or redteam)")
parser.add_argument("--workers", type=int, default=1, help="attempts run in parallel, each in its own sandbox")
args = parser.parse_args()

tasks = sorted(p for p in Path(args.dir).iterdir() if (p / "prompt.txt").exists())
wanted = Path(args.tasks).read_text().split() if str(args.tasks).endswith(".txt") else str(args.tasks).split(",")
tasks = [t for t in tasks if not args.tasks or t.name in wanted]
out = Path("results") / args.run_id
(out / "traces").mkdir(parents=True, exist_ok=True)
rows = read_jsonl(out / "results.jsonl")
finished = {(row["task"], row["repeat"]) for row in rows}           # for resuming
stamp = {**provenance(MODEL, SERVER), "think": THINK, "max_tokens": MAX_TOKENS, **SWITCHES}  # commit, model, switches
# Resuming with other code, another model or other switches would mix two experiments in one run.
keys = ("commit", "model_digest", "think", "max_tokens", *SWITCHES)
changed = sorted({key for row in rows for key in keys if row.get(key, stamp[key]) != stamp[key]})
if changed:
    sys.exit(f"This run was started with a different {' and '.join(changed)}. Use a new --run-id.")
# If Docker cannot start a container, stop the whole run: a crashed sandbox would look like a failed attempt.
docker_ok = lambda: sandbox.run(out, "true")[0] == 0 or sys.exit("Docker is not working. Fix it and rerun to resume.")  # noqa: E731


def attempt(task: Path, repeat: int) -> tuple[dict, list[dict]]:
    """One attempt at one task: a fresh copy, the agent, the grade. Returns its result line and its trace."""
    seed = zlib.crc32(f"{task.name}:{repeat}".encode())            # same task + repeat -> same seed
    workdir = Path(tempfile.mkdtemp(prefix="agent-"))              # a fresh copy of the buggy project
    shutil.copytree(task / "repo", workdir, dirs_exist_ok=True)
    start = time.time()
    docker_ok()                                                    # never blame the agent for a broken Docker
    server = [sys.executable, "mcp_server.py", str(workdir)]       # with MCP: one tool server per attempt
    report = (task / "prompt.txt").read_text(encoding="utf-8")
    with (mcp_session(server) if MCP else contextlib.nullcontext(FIXER_TOOLS)) as tools:
        trace = run_agent(report, workdir, seed, task / "repo" / "src", tools)
    diff = diff_dirs(task / "repo" / "src", workdir / "src")        # what the agent changed
    result = grade(task, workdir)
    shutil.rmtree(workdir, ignore_errors=True)
    docker_ok()                                                    # still working? otherwise this attempt is not saved

    harness = ("EXPLORE", "REVIEW", "RETRY", "SAMPLE", "STOP")         # steps that are not the fixer's own
    actions = [s["action"] for s in trace if s["action"] not in ("EXPLORE", "REVIEW")]
    said_done = actions[-1:] == ["done"]                                 # how the last try ended
    outcome = ("passed" if result["passed"] else "tampered" if result["tampered"]
               else "wrong_fix" if said_done else "ran_out_of_steps")
    verdicts = {s["action"]: s["result"] for s in trace if s["action"] in ("EXPLORE", "REVIEW", "STOP")}
    marker = (task / "injection.txt").read_text().strip() if (task / "injection.txt").exists() else ""  # red-team
    followed = bool(re.search(marker, json.dumps([s.get("args") for s in trace]))) if marker else None
    tokens = [sum(s[key] for s in trace) for key in ("tokens_in", "tokens_out")]
    record = {"task": task.name, "repeat": repeat, "seed": seed, **result, "outcome": outcome,
              "steps": len({s["step"] for s in trace if s["action"] not in harness}),
              "tries": 1 + actions.count("RETRY") + actions.count("SAMPLE"), "samples": 1 + actions.count("SAMPLE"),
              "guess": verdicts.get("EXPLORE"), "review": verdicts.get("REVIEW"), "stop": verdicts.get("STOP"),
              "malformed": actions.count("malformed"), "injection_followed": followed,
              "tokens_in": tokens[0], "tokens_out": tokens[1],
              "cost_usd": (tokens[0] * PRICES[0] + tokens[1] * PRICES[1]) / 1e6,   # 0 for local models
              "seconds": round(time.time() - start, 1), **stamp, "diff": diff}
    return record, trace


# All tasks once, then all tasks again, ... (so partial runs stay even). Results are saved in this order.
jobs = [(task, repeat) for repeat in range(args.repeats) for task in tasks if (task.name, repeat) not in finished]
with ThreadPoolExecutor(args.workers) as pool:
    for record, trace in pool.map(lambda job: attempt(*job), jobs):
        name = f"{record['task']}__r{record['repeat']}"
        (out / "traces" / f"{name}.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
        append_jsonl(out / "results.jsonl", record)
        print(f"{name}: {record['outcome']} ({record['steps']} steps, {record['seconds']}s)", flush=True)
