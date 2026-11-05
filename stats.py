"""Is a result real? Capability vs reliability, a confidence interval, and the run-to-run noise band.

    python stats.py results/baseline                     # analyse one run
    python stats.py results/baseline results/my-change   # is my-change really different from the baseline?
"""

import sys
from pathlib import Path
from statistics import mean, stdev

from utils import bootstrap, by_task, pass_at_k, pass_hat_k, read_jsonl

sys.stdout.reconfigure(encoding="utf-8")                 # so "±" prints correctly on Windows consoles too
runs = [read_jsonl(Path(folder) / "results.jsonl") for folder in sys.argv[1:]]
base = by_task(runs[0])                                  # task -> [True, False, ...], one entry per repeat
n = min(len(tries) for tries in base.values())           # repeats per task
pass_rate = lambda tasks: mean(x for tries in tasks for x in tries)  # noqa: E731  share of all attempts that passed

# 1. Capability vs reliability. pass@k = "at least one of k tries passes", pass^k = "all k tries pass".
print(f"{sys.argv[1]}: {len(runs[0])} attempts, {len(base)} tasks, {n} repeats each\n\n k   pass@k   pass^k")
for k in range(1, n + 1):
    at_k = mean(pass_at_k(sum(tries), len(tries), k) for tries in base.values())
    hat_k = mean(pass_hat_k(sum(tries), len(tries), k) for tries in base.values())
    print(f"{k:>2}  {at_k:7.0%}  {hat_k:7.0%}")

# 2. Confidence interval: resample the tasks 10,000 times and see how much pass@1 moves.
low, high = bootstrap(list(base.values()), pass_rate)
print(f"\npass@1 = {pass_rate(base.values()):.0%}, 95% CI [{low:.0%}, {high:.0%}]")

# 3. Noise band: each repeat is a full pass over all tasks, so the spread between repeats is pure luck.
per_repeat = [mean(r["passed"] for r in runs[0] if r["repeat"] == i) for i in range(n)]
band = 1.96 * stdev(per_repeat) * (2 / n) ** 0.5         # how far two n-repeat runs of the same agent can differ
print(f"repeats scored {', '.join(f'{p:.0%}' for p in per_repeat)}: two runs of the same agent "
      f"can differ by ±{band:.0%} by luck alone (noise band)")

# 4. Compare a second run with the first, task by task (only when two folders are given).
if len(runs) == 2:
    other = by_task(runs[1])
    pairs = [(tries, other[task]) for task, tries in base.items() if task in other]   # only tasks both runs have
    diff = lambda ps: pass_rate(b for _, b in ps) - pass_rate(a for a, _ in ps)  # noqa: E731
    low, high = bootstrap(pairs, diff)
    real = (low > 0 or high < 0) and abs(diff(pairs)) > band   # CI excludes 0 AND bigger than luck
    print(f"\n{sys.argv[2]} vs {sys.argv[1]} on {len(pairs)} shared tasks: pass@1 {diff(pairs):+.0%}, 95% CI [{low:+.0%}, {high:+.0%}] "
          f"-> {'REAL difference' if real else 'within noise'}")
