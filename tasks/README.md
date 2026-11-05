# Tasks

Each folder is one bug-fixing task:

| Path | What it is |
|---|---|
| `prompt.txt` | The bug report the agent receives |
| `repo/` | The buggy project the agent starts from: `src/`, `tests/test_visible.py`, `pytest.ini` |
| `hidden/test_hidden.py` | Extra tests used only for grading; the agent never sees them |
| `solution/` | The correct version of the file(s) that contain the bug |

There are 45 tasks, 5 from each of the 9 projects in [`../corpus/`](../corpus/), made by
[`../make_tasks.py`](../make_tasks.py). The id says the project and the difficulty (a letter is added when a
project has several of one kind): `d1` = bug in a function the test calls, `d2` = bug in a helper one
call away, `d3` = two bugs in two files.

| Task | Difficulty | File | Correct code | Buggy code |
|---|---|---|---|---|
| inventory-d1 | D1 | `src/stock.py` | `return self.on_hand(sku) - self.reserved.get(sku, 0)` | `return self.on_hand(sku) + self.reserved.get(sku, 0)` |
| inventory-d2 | D2 | `src/stock.py` | `if qty > held:` | `if qty >= held:` |
| inventory-d2b | D2 | `src/stock.py` | `held = self.reserved.get(sku, 0)` | (line deleted) |
| inventory-d3 | D3 | `src/ledger.py` | `self.entries.append((sku, delta, reason))` | (line deleted) |
| inventory-d3 | D3 | `src/stock.py` | `held = self.reserved.get(sku, 0)` | `held = self.reserved.get(0, sku)` |
| inventory-d3b | D3 | `src/ledger.py` | `return sum(delta for item, delta, _ in self.entries if item == sku)` | `return sum(delta for item, delta, _ in self.entries if item != sku)` |
| inventory-d3b | D3 | `src/stock.py` | `self.reserved[sku] = held - qty` | `self.reserved[sku] = held + qty` |
| invoice-d1 | D1 | `src/invoice.py` | `return percent_of(self.subtotal() - self.discount(), self.tax_bp)` | (line deleted) |
| invoice-d2 | D2 | `src/money.py` | `sign = "-" if cents < 0 else ""` | `sign = "-" if cents > 0 else ""` |
| invoice-d2b | D2 | `src/money.py` | `quotient, remainder = divmod(product, 10000)` | (line deleted) |
| invoice-d3 | D3 | `src/invoice.py` | `if not 0 <= basis_points <= 10000:` | `if not 0 >= basis_points <= 10000:` |
| invoice-d3 | D3 | `src/money.py` | `product = abs(cents) * basis_points` | (line deleted) |
| invoice-d3b | D3 | `src/invoice.py` | `"total": format_cents(self.total()),` | (line deleted) |
| invoice-d3b | D3 | `src/money.py` | `return quotient if cents >= 0 else -quotient` | (line deleted) |
| kvconfig-d1 | D1 | `src/settings.py` | `return settings.get(section, {}).get(key.lower(), fallback)` | (line deleted) |
| kvconfig-d2 | D2 | `src/lexer.py` | `name = line[1:-1].strip().lower()` | (line deleted) |
| kvconfig-d2b | D2 | `src/lexer.py` | `elif ch in COMMENT_CHARS:` | (line deleted) |
| kvconfig-d3 | D3 | `src/lexer.py` | `elif ch in QUOTES:` | `elif ch not in QUOTES:` |
| kvconfig-d3 | D3 | `src/settings.py` | `section = payload` | (line deleted) |
| kvconfig-d3b | D3 | `src/lexer.py` | `return ("section", name)` | (line deleted) |
| kvconfig-d3b | D3 | `src/settings.py` | `section, _, key = dotted.rpartition(".")` | (line deleted) |
| numtools-d1 | D1 | `src/numtools.py` | `return ordered[_rank_index(len(ordered), pct / 100)]` | `return ordered[_rank_index(pct / 100, len(ordered))]` |
| numtools-d1b | D1 | `src/numtools.py` | `total += value` | `total -= value` |
| numtools-d1c | D1 | `src/numtools.py` | `if index >= window:` | `if index > window:` |
| numtools-d2 | D2 | `src/numtools.py` | `return clamp(rank, 1, count) - 1` | `return clamp(rank, 1, count) + 1` |
| numtools-d2b | D2 | `src/numtools.py` | `rank = math.ceil(fraction * count)` | (line deleted) |
| recent-d1 | D1 | `src/recent.py` | `self._touch(key)` | (line deleted) |
| recent-d1b | D1 | `src/recent.py` | `self._evict(self._order[0])` | `self._evict(self._order[-1])` |
| recent-d1c | D1 | `src/recent.py` | `return self._data[key][0]` | (line deleted) |
| recent-d2 | D2 | `src/recent.py` | `self._order.append(key)` | (line deleted) |
| recent-d2b | D2 | `src/recent.py` | `self._order.remove(key)` | (line deleted) |
| ringlog-d1 | D1 | `src/ringlog.py` | `if count <= 0:` | `if count >= 0:` |
| ringlog-d1b | D1 | `src/ringlog.py` | `self._start = self._index(1)` | (line deleted) |
| ringlog-d1c | D1 | `src/ringlog.py` | `return self.snapshot()[-count:]` | (line deleted) |
| ringlog-d1d | D1 | `src/ringlog.py` | `if self._size == 0:` | `if self._size != 0:` |
| ringlog-d1e | D1 | `src/ringlog.py` | `self._slots[self._start] = item` | (line deleted) |
| snapshots-d1 | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = existing[-1] - 1 if existing else 1` |
| snapshots-d1b | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = existing[0] + 1 if existing else 1` |
| snapshots-d1c | D1 | `src/snapshots.py` | `return number` | (line deleted) |
| snapshots-d1d | D1 | `src/snapshots.py` | `existing = list_snapshots(folder)` | (line deleted) |
| snapshots-d1e | D1 | `src/snapshots.py` | `elif number < 0:` | (line deleted) |
| timespan-d1 | D1 | `src/timespan.py` | `total = 0` | `total = 1` |
| timespan-d1b | D1 | `src/timespan.py` | `if len(parts) == max_units:` | `if len(parts) != max_units:` |
| timespan-d1c | D1 | `src/timespan.py` | `total += amount * UNIT_SECONDS[unit]` | (line deleted) |
| timespan-d2 | D2 | `src/timespan.py` | `number += ch` | `number -= ch` |
| timespan-d2b | D2 | `src/timespan.py` | `if number:` | (line deleted) |
| workdays-d1 | D1 | `src/workdays.py` | `current += timedelta(days=step)` | `current -= timedelta(days=step)` |
| workdays-d1b | D1 | `src/workdays.py` | `count += 1` | `count -= 1` |
| workdays-d2 | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | `return (date(year, month + 1, 1) - date(month, year, 1)).days` |
| workdays-d2b | D2 | `src/workdays.py` | `if month == 12:` | `if month != 12:` |
| workdays-d2c | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | `return (date(year, month - 1, 1) - date(year, month, 1)).days` |

## Held out

These 9 tasks (one per project, listed in [`held_out.txt`](held_out.txt)) are never read while designing a stage: their traces stay unopened and no
prompt or tool is tuned on them. They are graded in every run, so a stage that only works on the tasks it was
tuned on shows up as a gap between the two groups (`report.py` prints pass@1 for each).

`inventory-d2b`, `invoice-d2b`, `kvconfig-d1`, `numtools-d1c`, `recent-d2b`, `ringlog-d1e`, `snapshots-d1d`, `timespan-d1c`, `workdays-d2b`
