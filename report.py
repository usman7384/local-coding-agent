"""Summarise a run: how often the agent succeeds, how consistently, and why it fails.

    python report.py results/baseline
"""

import json
import sys
from collections import Counter
from pathlib import Path

from utils import by_task, read_jsonl, stalls

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
retried = [r for r in rows if r.get("tries", 1) > 1]                   # verify failed, so a second try ran
print(f"retries: {len(retried)} attempts got a second try, {sum(r['passed'] for r in retried)} of them passed")
sampled = [r for r in rows if r.get("samples", 1) > 1]                  # best-of-N needed another sample
if sampled:
    print(f"best-of-N: {len(sampled)} attempts needed another sample, {sum(r['passed'] for r in sampled)} passed")
guessed = [r for r in rows if r.get("guess")]                           # the explorer named a place
reviewed = [r for r in rows if r.get("review")]                         # the critic read a green fix
rejected = [r for r in reviewed if r["review"].startswith("REJECT")]
print(f"explorer: a guess in {len(guessed)} of {len(rows)} attempts, {sum(r['passed'] for r in guessed)} passed; "
      f"critic: {len(reviewed)} reviews, {len(rejected)} rejections, {sum(r['passed'] for r in rejected)} passed")
print(f"malformed tool calls: {sum(r['malformed'] for r in rows)} in {sum(r['steps'] for r in rows)} steps")

traces = [json.loads(t.read_text(encoding="utf-8")) for t in run.glob("traces/*.json")]
# Stalls: test runs that failed exactly like the failing run before them, so the steps between made no progress.
counts = [stalls(trace) for trace in traces]
print(f"stalls: {sum(counts)} repeated failing test runs, in {sum(c > 0 for c in counts)} of {len(counts)} attempts")

# Edits: how many applied, and how many failed because the old text is not in the file (edited from memory).
edits = [s["result"] for trace in traces for s in trace if s["action"].lower() == "edit"]  # old runs: "EDIT"
print(f"edits: {len(edits)}, applied {sum(e.lower().startswith('edit applied') for e in edits) / max(len(edits), 1):.0%}, "
      f"old text not found {sum('appears 0 times' in e for e in edits) / max(len(edits), 1):.0%}")

# Cost: tokens instead of seconds, because seconds depend on how busy the GPU is.
counted = [r for r in rows if "tokens_in" in r]
tokens, wins = sum(r["tokens_in"] + r["tokens_out"] for r in counted), sum(r["passed"] for r in counted)
if counted:
    per_success = f"{tokens / wins:,.0f} per success" if wins else "no successes to divide by"
    print(f"tokens: {tokens / len(counted):,.0f} per attempt, {per_success}")
cost = sum(r.get("cost_usd", 0) for r in rows)                          # API models only; local models cost 0
print(f"cost: ${cost:,.2f}, ${cost / max(sum(r['passed'] for r in rows), 1):,.3f} per success" if cost else "cost: $0 (local)")
print("code and model:", sorted({(r.get("commit", "?"), r.get("model_digest", "?")) for r in rows}))
print("for confidence intervals and the noise band: python stats.py", sys.argv[1])
