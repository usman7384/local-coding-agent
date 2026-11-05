"""Summarise a run: how often the agent succeeds, how consistently, and why it fails.

    python report.py results/baseline
"""

import json
import sys
from collections import Counter
from pathlib import Path

from utils import by_task, read_jsonl

run = Path(sys.argv[1])
rows = read_jsonl(run / "results.jsonl")
passes = by_task(rows)                                    # task -> [True, False, ...] one per repeat

print("| task | passed |\n|---|---|")
for task, results in sorted(passes.items()):
    print(f"| {task} | {sum(results)}/{len(results)} |")

pass_at_1 = sum(r["passed"] for r in rows) / len(rows)                    # how often it works
pass_all = sum(all(results) for results in passes.values()) / len(passes)  # how reliably it works
print(f"\npass@1   (share of attempts that passed):     {pass_at_1:.0%} of {len(rows)} attempts")
print(f"pass-all (share of tasks that passed every run): {pass_all:.0%} of {len(passes)} tasks")
held_out = set(Path("tasks/held_out.txt").read_text(encoding="utf-8").split())  # never used to design a stage
groups = {"tuning": [r for r in rows if r["task"] not in held_out], "held out": [r for r in rows if r["task"] in held_out]}
print("pass@1 by group:", ", ".join(f"{name} {sum(r['passed'] for r in g) / len(g):.0%} of {len(g)}"
                                    for name, g in groups.items() if g))
print("outcomes:", dict(Counter(r["outcome"] for r in rows)))
print(f"malformed replies: {sum(r['malformed'] for r in rows)} of {sum(r['steps'] for r in rows)} steps")

# Edits: how many applied, and how many failed because the OLD text is not in the file (edited from memory).
edits = [s["result"] for t in run.glob("traces/*.json") for s in json.loads(t.read_text(encoding="utf-8"))
         if s["action"] == "EDIT"]
print(f"edits: {len(edits)}, applied {sum(e.startswith('EDIT applied') for e in edits) / max(len(edits), 1):.0%}, "
      f"OLD text not found {sum('appears 0 times' in e for e in edits) / max(len(edits), 1):.0%}")

# Cost: tokens instead of seconds, because seconds depend on how busy the GPU is.
counted = [r for r in rows if "tokens_in" in r]
tokens, wins = sum(r["tokens_in"] + r["tokens_out"] for r in counted), sum(r["passed"] for r in counted)
if counted:
    per_success = f"{tokens / wins:,.0f} per success" if wins else "no successes to divide by"
    print(f"tokens: {tokens / len(counted):,.0f} per attempt, {per_success}")
print("code and model:", sorted({(r.get("commit", "?"), r.get("model_digest", "?")) for r in rows}))
print("for confidence intervals and the noise band: python stats.py", sys.argv[1])
