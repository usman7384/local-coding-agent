"""Summarise a run: how often the agent succeeds, how consistently, and why it fails.

    python report.py results/baseline
"""

import sys
from collections import Counter
from pathlib import Path

from utils import by_task, read_jsonl

rows = read_jsonl(Path(sys.argv[1]) / "results.jsonl")
passes = by_task(rows)                                    # task -> [True, False, ...] one per repeat

print("| task | passed |\n|---|---|")
for task, results in sorted(passes.items()):
    print(f"| {task} | {sum(results)}/{len(results)} |")

pass_at_1 = sum(r["passed"] for r in rows) / len(rows)                    # how often it works
pass_all = sum(all(results) for results in passes.values()) / len(passes)  # how reliably it works
print(f"\npass@1   (share of attempts that passed):     {pass_at_1:.0%} of {len(rows)} attempts")
print(f"pass-all (share of tasks that passed every run): {pass_all:.0%} of {len(passes)} tasks")
print("outcomes:", dict(Counter(r["outcome"] for r in rows)))
print(f"malformed replies: {sum(r['malformed'] for r in rows)} of {sum(r['steps'] for r in rows)} steps")
print("for confidence intervals and the noise band: python stats.py", sys.argv[1])
