"""Run every task several times and save one result line per attempt.

    python run.py --run-id baseline --repeats 3
    python run.py --run-id smoke --repeats 1 --tasks ringlog-d1,timespan-d1

Finished attempts are skipped, so an interrupted run can simply be started again.
"""

import argparse
import json
import shutil
import sys
import tempfile
import time
import zlib
from pathlib import Path

import sandbox
from agent import MODEL, SERVER, run_agent
from grade import grade
from utils import append_jsonl, diff_dirs, provenance, read_jsonl

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", default="baseline")
parser.add_argument("--repeats", type=int, default=3)
parser.add_argument("--tasks", help="comma-separated task ids (default: all)")
args = parser.parse_args()

tasks = sorted(p for p in Path("tasks").iterdir() if (p / "prompt.txt").exists())
tasks = [t for t in tasks if not args.tasks or t.name in args.tasks.split(",")]
out = Path("results") / args.run_id
(out / "traces").mkdir(parents=True, exist_ok=True)
rows = read_jsonl(out / "results.jsonl")
finished = {(row["task"], row["repeat"]) for row in rows}           # for resuming
stamp = provenance(MODEL, SERVER)                                    # commit, model digest, Ollama version
# Resuming with other code or another model would mix two experiments in one run.
changed = sorted({key for row in rows for key in ("commit", "model_digest") if row.get(key, stamp[key]) != stamp[key]})
if changed:
    sys.exit(f"This run was started with a different {' and '.join(changed)}. Use a new --run-id.")
# If Docker cannot start a container, stop the whole run: a crashed sandbox would look like a failed attempt.
docker_ok = lambda: sandbox.run(out, "true")[0] == 0 or sys.exit("Docker is not working. Fix it and rerun to resume.")  # noqa: E731

for repeat in range(args.repeats):          # all tasks once, then all tasks again, ... (so partial runs stay even)
    for task in tasks:
        if (task.name, repeat) in finished:
            continue
        seed = zlib.crc32(f"{task.name}:{repeat}".encode())        # same task + repeat -> same seed
        workdir = Path(tempfile.mkdtemp(prefix="agent-"))          # a fresh copy of the buggy project
        shutil.copytree(task / "repo", workdir, dirs_exist_ok=True)
        start = time.time()

        docker_ok()                                                # never blame the agent for a broken Docker
        trace = run_agent((task / "prompt.txt").read_text(encoding="utf-8"), workdir, seed)
        diff = diff_dirs(task / "repo" / "src", workdir / "src")    # what the agent changed
        result = grade(task, workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        docker_ok()                                                # still working? otherwise this attempt is not saved

        said_done = bool(trace) and trace[-1]["action"] == "DONE"
        outcome = ("passed" if result["passed"] else "tampered" if result["tampered"]
                   else "wrong_fix" if said_done else "ran_out_of_steps")
        record = {"task": task.name, "repeat": repeat, "seed": seed, **result, "outcome": outcome,
                  "steps": len(trace), "malformed": sum(s["action"] == "MALFORMED" for s in trace),
                  "tokens_in": sum(s["tokens_in"] for s in trace), "tokens_out": sum(s["tokens_out"] for s in trace),
                  "seconds": round(time.time() - start, 1), **stamp, "diff": diff}
        (out / "traces" / f"{task.name}__r{repeat}.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
        append_jsonl(out / "results.jsonl", record)
        print(f"{task.name} repeat {repeat}: {outcome} ({record['steps']} steps, {record['seconds']}s)", flush=True)
