"""Best-of-N without a new run: replay a run's repeats as if they were N attempts at the same task.

Best-of-N runs up to N attempts and keeps the first whose visible tests pass (the verifier); if none passes,
it keeps the last. Every order of a task's repeats is tried, so the numbers do not depend on which came first.

    python bestofn.py results/stage-5a results/bench-45
"""

import sys
from itertools import permutations
from pathlib import Path
from statistics import mean

from utils import by_task, pass_at_k, read_jsonl

for folder in sys.argv[1:]:
    rows = read_jsonl(Path(folder) / "results.jsonl")
    tasks = {}
    for r in rows:
        tasks.setdefault(r["task"], []).append(r)
    print(f"{folder}\n N   best-of-N   tokens per task   per success   oracle pass@N")
    for n in range(1, min(len(rs) for rs in tasks.values()) + 1):
        wins, tokens = [], []
        for rs in tasks.values():
            for order in permutations(rs, n):
                pick = next((r for r in order if r["visible_ok"]), order[-1])     # first green, else the last
                wins.append(pick["passed"])                                       # graded by the hidden tests
                tokens.append(sum(r["tokens_in"] + r["tokens_out"] for r in order[:order.index(pick) + 1]))
        oracle = mean(pass_at_k(sum(t), len(t), n) for t in by_task(rows).values())  # a perfect verifier
        print(f"{n:>2}   {mean(wins):9.0%}   {mean(tokens):15,.0f}   {sum(tokens) / sum(wins):11,.0f}   {oracle:13.0%}")
