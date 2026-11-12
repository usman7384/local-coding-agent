"""Opt-in self-improvement: distil lessons from graded runs, and promote them only if they help on unseen tasks.

    python learn.py results/<run>                                 # writes memory/candidate.md
    AGENT_MEMORY=memory/candidate.md python run.py --run-id <with>  # the agent with the candidate lessons
    python learn.py --promote results/<without> results/<with>    # candidate -> memory/lessons.md, if it helps

Only tuning tasks feed the lessons; held-out tasks only judge them, so the held-out score stays an honest test.
"""

import argparse
import shutil
from pathlib import Path
from statistics import mean

from agent import PROMPTS, ask_model
from utils import bootstrap, by_task, read_jsonl, shorten

parser = argparse.ArgumentParser()
parser.add_argument("runs", nargs="+", help="one run to learn from, or (with --promote) the runs without and with")
parser.add_argument("--promote", action="store_true")
parser.add_argument("--memory", default="memory")
args = parser.parse_args()
memory, held_out = Path(args.memory), set(Path("tasks/held_out.txt").read_text(encoding="utf-8").split())
memory.mkdir(exist_ok=True)

if args.promote:                    # eval-gated rollout: paired held-out tasks, a bootstrap interval above zero
    before, after = (by_task([r for r in read_jsonl(Path(run) / "results.jsonl") if r["task"] in held_out])
                     for run in args.runs)
    pairs = [(before[task], after[task]) for task in before if task in after]
    low, high = bootstrap(pairs, lambda ps: mean(x for _, b in ps for x in b) - mean(x for a, _ in ps for x in a))
    gain = low > 0
    if gain:
        shutil.copyfile(memory / "candidate.md", memory / "lessons.md")
    print(f"held-out difference CI [{low:+.0%}, {high:+.0%}]: {'promoted' if gain else 'kept the current lessons'}")
else:                               # distil: failures teach most, a few passes show what works
    rows = [r for r in read_jsonl(Path(args.runs[0]) / "results.jsonl") if r["task"] not in held_out]
    shown = [r for r in rows if not r["passed"]][:20] + [r for r in rows if r["passed"]][:10]
    current = (memory / "lessons.md").read_text(encoding="utf-8") if (memory / "lessons.md").exists() else "(none)"
    attempts = "\n\n".join(f"{r['task']}: {r['outcome']}\n{shorten(r['diff'], 400)}" for r in shown)
    task = f"Current lessons:\n{current}\n\nAttempts:\n\n{attempts}"
    message, _ = ask_model([{"role": "system", "content": PROMPTS["learner"]}, {"role": "user", "content": task}], [], 0)
    (memory / "candidate.md").write_text(message.get("content") or "", encoding="utf-8")
    print(message.get("content"))
