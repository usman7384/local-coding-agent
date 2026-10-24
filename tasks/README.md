# Tasks

Each folder is one bug-fixing task:

| Path | What it is |
|---|---|
| `prompt.txt` | The bug report the agent receives |
| `repo/` | The buggy project the agent starts from: `src/`, `tests/test_visible.py`, `pytest.ini` |
| `hidden/test_hidden.py` | Extra tests used only for grading; the agent never sees them |
| `solution/` | The correct version of the file(s) that contain the bug |

The id suffix is the difficulty: `d1` = bug in a function the test calls, `d2` = bug in a helper one
call away, `d3` = two bugs in two files.

| Task | Difficulty | File | Correct code | Buggy code |
|---|---|---|---|---|
| inventory-d2 | D2 | `src/stock.py` | `if qty > held:` | `if qty >= held:` |
| inventory-d3 | D3 | `src/ledger.py` | `self.entries.append((sku, delta, reason))` | (line deleted) |
| inventory-d3 | D3 | `src/stock.py` | `held = self.reserved.get(sku, 0)` | `held = self.reserved.get(0, sku)` |
| invoice-d2 | D2 | `src/money.py` | `sign = "-" if cents < 0 else ""` | `sign = "-" if cents > 0 else ""` |
| invoice-d3 | D3 | `src/money.py` | `product = abs(cents) * basis_points` | (line deleted) |
| invoice-d3 | D3 | `src/invoice.py` | `if not 0 <= basis_points <= 10000:` | `if not 0 >= basis_points <= 10000:` |
| kvconfig-d2 | D2 | `src/lexer.py` | `name = line[1:-1].strip().lower()` | (line deleted) |
| kvconfig-d3 | D3 | `src/lexer.py` | `elif ch in QUOTES:` | `elif ch not in QUOTES:` |
| kvconfig-d3 | D3 | `src/settings.py` | `section = payload` | (line deleted) |
| numtools-d1 | D1 | `src/numtools.py` | `return ordered[_rank_index(len(ordered), pct / 100)]` | `return ordered[_rank_index(pct / 100, len(ordered))]` |
| numtools-d2 | D2 | `src/numtools.py` | `return clamp(rank, 1, count) - 1` | `return clamp(rank, 1, count) + 1` |
| recent-d1 | D1 | `src/recent.py` | `self._touch(key)` | (line deleted) |
| ringlog-d1 | D1 | `src/ringlog.py` | `if count <= 0:` | `if count >= 0:` |
| snapshots-d1 | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = existing[-1] - 1 if existing else 1` |
| timespan-d1 | D1 | `src/timespan.py` | `total = 0` | `total = 1` |
| timespan-d2 | D2 | `src/timespan.py` | `number += ch` | `number -= ch` |
| workdays-d1 | D1 | `src/workdays.py` | `current += timedelta(days=step)` | `current -= timedelta(days=step)` |
| workdays-d2 | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | `return (date(year, month + 1, 1) - date(month, year, 1)).days` |
