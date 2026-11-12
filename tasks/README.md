# Tasks

Each folder is one bug-fixing task:

| Path | What it is |
|---|---|
| `prompt.txt` | The bug report the agent receives |
| `repo/` | The buggy project the agent starts from: `src/`, `tests/test_visible.py`, `pytest.ini` |
| `hidden/test_hidden.py` | Extra tests used only for grading; the agent never sees them |
| `solution/` | The correct version of the file(s) that contain the bug |

There are 125 tasks, 8 from each of the 15 projects in [`../corpus/`](../corpus/) (7 from inventory) plus 6 D4 tasks, made by
[`../make_tasks.py`](../make_tasks.py). The id says the project and the difficulty (a letter is added when a
project has several of one kind): `d1` = bug in a function the test calls, `d2` = bug in a helper one
call away, `d3` = two bugs in two files, `d4` = three bugs in three files.

| Task | Difficulty | File | Correct code | Buggy code |
|---|---|---|---|---|
| booking-d1 | D1 | `src/planner.py` | `return used * 100 // (DAY_END - DAY_START)` | (line deleted) |
| booking-d1b | D1 | `src/slots.py` | `else:` | (line deleted) |
| booking-d1c | D1 | `src/slots.py` | `return int(hours) * 60 + int(minutes)` | (line deleted) |
| booking-d2 | D2 | `src/slots.py` | `cursor = start` | (line deleted) |
| booking-d2b | D2 | `src/rooms.py` | `return [(start, end) for start, end, _ in self.bookings]` | `return` |
| booking-d2c | D2 | `src/planner.py` | `return room` | `return name` |
| booking-d2d | D2 | `src/rooms.py` | `return total` | (line deleted) |
| booking-d3 | D3 | `src/planner.py` | `room = min(fits, key=lambda r: r.capacity)` | (line deleted) |
| booking-d3 | D3 | `src/slots.py` | `if b_start > cursor:` | `if b_start > busy:` |
| booking-d4 | D4 | `src/planner.py` | `return used * 100 // (DAY_END - DAY_START)` | (line deleted) |
| booking-d4 | D4 | `src/rooms.py` | `return [(start, end) for start, end, _ in self.bookings]` | `return` |
| booking-d4 | D4 | `src/slots.py` | `cursor = start` | (line deleted) |
| gradebook-d1 | D1 | `src/report.py` | `result.append((student, rank))` | (line deleted) |
| gradebook-d1b | D1 | `src/report.py` | `if value is not None:` | `if student is not None:` |
| gradebook-d1c | D1 | `src/report.py` | `value = self.final(student)` | (line deleted) |
| gradebook-d2 | D2 | `src/weights.py` | `return (points * 2 + total) // (total * 2)` | `return (points * 2 - total) // (total * 2)` |
| gradebook-d2b | D2 | `src/scores.py` | `return (sum(values) * 2 + count) // (count * 2)` | `return (sum(values) * 2 - count) // (count * 2)` |
| gradebook-d2c | D2 | `src/report.py` | `if not values:` | `if not student:` |
| gradebook-d2d | D2 | `src/scores.py` | `return (points * 200 + possible) // (possible * 2)` | `return (points * 200 - possible) // (possible * 2)` |
| gradebook-d3 | D3 | `src/report.py` | `rank = index + 1` | `rank = index - 1` |
| gradebook-d3 | D3 | `src/scores.py` | `n = max(min(n, len(percents) - 1), 0)` | `n = min(min(n, len(percents) - 1), 0)` |
| gradebook-d4 | D4 | `src/report.py` | `if value is not None:` | `if student is not None:` |
| gradebook-d4 | D4 | `src/scores.py` | `return (sum(values) * 2 + count) // (count * 2)` | `return (sum(values) * 2 - count) // (count * 2)` |
| gradebook-d4 | D4 | `src/weights.py` | `return (points * 2 + total) // (total * 2)` | `return (points * 2 - total) // (total * 2)` |
| inventory-d1 | D1 | `src/stock.py` | `return self.on_hand(sku) - self.reserved.get(sku, 0)` | `return self.on_hand(sku) + self.reserved.get(sku, 0)` |
| inventory-d1b | D1 | `src/stock.py` | `self.reserved[sku] = self.reserved.get(sku, 0) + qty` | `self.reserved[sku] = self.reserved.get(sku, 0) + sku` |
| inventory-d2 | D2 | `src/stock.py` | `if qty > held:` | `if qty >= held:` |
| inventory-d2b | D2 | `src/stock.py` | `held = self.reserved.get(sku, 0)` | (line deleted) |
| inventory-d2c | D2 | `src/stock.py` | `self.reserved[sku] = held - qty` | `self.reserved[sku] = sku - qty` |
| inventory-d3 | D3 | `src/ledger.py` | `self.entries.append((sku, delta, reason))` | (line deleted) |
| inventory-d3 | D3 | `src/stock.py` | `held = self.reserved.get(sku, 0)` | `held = self.reserved.get(0, sku)` |
| inventory-d3b | D3 | `src/ledger.py` | `return sum(delta for item, delta, _ in self.entries if item == sku)` | `return sum(delta for item, delta, _ in self.entries if item != sku)` |
| inventory-d3b | D3 | `src/stock.py` | `self.reserved[sku] = held - qty` | `self.reserved[sku] = held + qty` |
| invoice-d1 | D1 | `src/invoice.py` | `return percent_of(self.subtotal() - self.discount(), self.tax_bp)` | (line deleted) |
| invoice-d1b | D1 | `src/invoice.py` | `return self.subtotal() - self.discount() + self.tax()` | `return self.subtotal() - self.discount() - self.tax()` |
| invoice-d2 | D2 | `src/money.py` | `sign = "-" if cents < 0 else ""` | `sign = "-" if cents > 0 else ""` |
| invoice-d2b | D2 | `src/money.py` | `quotient, remainder = divmod(product, 10000)` | (line deleted) |
| invoice-d2c | D2 | `src/money.py` | `return quotient if cents >= 0 else -quotient` | `return` |
| invoice-d3 | D3 | `src/invoice.py` | `if not 0 <= basis_points <= 10000:` | `if not 0 >= basis_points <= 10000:` |
| invoice-d3 | D3 | `src/money.py` | `product = abs(cents) * basis_points` | (line deleted) |
| invoice-d3b | D3 | `src/invoice.py` | `"total": format_cents(self.total()),` | (line deleted) |
| invoice-d3b | D3 | `src/money.py` | `return quotient if cents >= 0 else -quotient` | (line deleted) |
| invoice-d3c | D3 | `src/invoice.py` | `return percent_of(self.subtotal(), self.discount_bp)` | `return` |
| invoice-d3c | D3 | `src/money.py` | `return f"{sign}{whole}.{frac:02d}"` | `return` |
| kvconfig-d1 | D1 | `src/settings.py` | `return settings.get(section, {}).get(key.lower(), fallback)` | (line deleted) |
| kvconfig-d1b | D1 | `src/settings.py` | `result.setdefault(section, {})` | (line deleted) |
| kvconfig-d2 | D2 | `src/lexer.py` | `name = line[1:-1].strip().lower()` | (line deleted) |
| kvconfig-d2b | D2 | `src/lexer.py` | `elif ch in COMMENT_CHARS:` | (line deleted) |
| kvconfig-d2c | D2 | `src/lexer.py` | `return ("section", name)` | `return` |
| kvconfig-d3 | D3 | `src/lexer.py` | `elif ch in QUOTES:` | `elif ch not in QUOTES:` |
| kvconfig-d3 | D3 | `src/settings.py` | `section = payload` | (line deleted) |
| kvconfig-d3b | D3 | `src/lexer.py` | `return ("section", name)` | (line deleted) |
| kvconfig-d3b | D3 | `src/settings.py` | `section, _, key = dotted.rpartition(".")` | (line deleted) |
| kvconfig-d3c | D3 | `src/lexer.py` | `return line[:index]` | `return in_quote[:index]` |
| kvconfig-d3c | D3 | `src/settings.py` | `return value` | (line deleted) |
| numtools-d1 | D1 | `src/numtools.py` | `return ordered[_rank_index(len(ordered), pct / 100)]` | `return ordered[_rank_index(pct / 100, len(ordered))]` |
| numtools-d1b | D1 | `src/numtools.py` | `total += value` | `total -= value` |
| numtools-d1c | D1 | `src/numtools.py` | `if index >= window:` | `if index > window:` |
| numtools-d1d | D1 | `src/numtools.py` | `units = value / step` | (line deleted) |
| numtools-d1e | D1 | `src/numtools.py` | `return averages` | (line deleted) |
| numtools-d1f | D1 | `src/numtools.py` | `if index >= window - 1:` | `if index > window - 1:` |
| numtools-d2 | D2 | `src/numtools.py` | `return clamp(rank, 1, count) - 1` | `return clamp(rank, 1, count) + 1` |
| numtools-d2b | D2 | `src/numtools.py` | `rank = math.ceil(fraction * count)` | (line deleted) |
| recent-d1 | D1 | `src/recent.py` | `self._touch(key)` | (line deleted) |
| recent-d1b | D1 | `src/recent.py` | `self._evict(self._order[0])` | `self._evict(self._order[-1])` |
| recent-d1c | D1 | `src/recent.py` | `return self._data[key][0]` | (line deleted) |
| recent-d1d | D1 | `src/recent.py` | `if key not in self._data and len(self._data) >= self.capacity:` | `if key not in self._data and len(self._data) > self.capacity:` |
| recent-d1e | D1 | `src/recent.py` | `self._touch(key)` | `self._touch(default)` |
| recent-d2 | D2 | `src/recent.py` | `self._order.append(key)` | (line deleted) |
| recent-d2b | D2 | `src/recent.py` | `self._order.remove(key)` | (line deleted) |
| recent-d2c | D2 | `src/recent.py` | `value, _ = self._data.pop(key)` | (line deleted) |
| ringlog-d1 | D1 | `src/ringlog.py` | `if count <= 0:` | `if count >= 0:` |
| ringlog-d1b | D1 | `src/ringlog.py` | `self._start = self._index(1)` | (line deleted) |
| ringlog-d1c | D1 | `src/ringlog.py` | `return self.snapshot()[-count:]` | (line deleted) |
| ringlog-d1d | D1 | `src/ringlog.py` | `if self._size == 0:` | `if self._size != 0:` |
| ringlog-d1e | D1 | `src/ringlog.py` | `self._slots[self._start] = item` | (line deleted) |
| ringlog-d1f | D1 | `src/ringlog.py` | `return [self._slots[self._index(i)] for i in range(self._size)]` | `return` |
| ringlog-d1g | D1 | `src/ringlog.py` | `return self.snapshot()[-count:]` | `return` |
| ringlog-d1h | D1 | `src/ringlog.py` | `self._start = self._index(1)` | (line deleted) |
| router-d1 | D1 | `src/router.py` | `hit = match_route(specs, parts)` | `found = match_route(specs, parts)` |
| router-d1b | D1 | `src/router.py` | `if not found:` | (line deleted) |
| router-d1c | D1 | `src/router.py` | `raise LookupError("not found: " + path)` | `raise LookupError("not found: " - path)` |
| router-d2 | D2 | `src/router.py` | `return {}, 1, 1` | (line deleted) |
| router-d2b | D2 | `src/router.py` | `return params, weights` | (line deleted) |
| router-d2c | D2 | `src/convert.py` | `return int(text)` | (line deleted) |
| router-d2d | D2 | `src/convert.py` | `if kind != "path" and kind not in CONVERTERS:` | `if kind == "path" and kind not in CONVERTERS:` |
| router-d3 | D3 | `src/router.py` | `return name, params` | `return` |
| router-d3 | D3 | `src/segments.py` | `if part[i] == "%" and is_hex(code):` | `if part[i] == "%" and is_hex(part):` |
| router-d4 | D4 | `src/convert.py` | `return int(text)` | (line deleted) |
| router-d4 | D4 | `src/router.py` | `hit = match_route(specs, parts)` | `found = match_route(specs, parts)` |
| router-d4 | D4 | `src/segments.py` | `if part[i] == "%" and is_hex(code):` | `if part[i] == "%" and is_hex(part):` |
| shipping-d1 | D1 | `src/quote.py` | `return 0` | `return` |
| shipping-d1b | D1 | `src/quote.py` | `return self.subtotal()` | `return` |
| shipping-d1c | D1 | `src/quote.py` | `self.parcels.append((grams, length, width, height))` | `self.parcels.append((width, length, width, height))` |
| shipping-d2 | D2 | `src/quote.py` | `return 0` | `return` |
| shipping-d2b | D2 | `src/rates.py` | `if grams % 1000 > 0:` | `if whole % 1000 > 0:` |
| shipping-d2c | D2 | `src/zones.py` | `return COUNTRIES.get(country, "world")` | `return COUNTRIES.get(postcode, "world")` |
| shipping-d2d | D2 | `src/rates.py` | `return BASE_PRICE + extra_kg(grams) * PER_KG` | `return BASE_PRICE - extra_kg(grams) * PER_KG` |
| shipping-d3 | D3 | `src/quote.py` | `return length * width * height * 1000 // VOLUME_DIVISOR` | `return length * width * width * 1000 // VOLUME_DIVISOR` |
| shipping-d3 | D3 | `src/rates.py` | `whole += 1` | `grams += 1` |
| shipping-d4 | D4 | `src/quote.py` | `return 0` | `return` |
| shipping-d4 | D4 | `src/rates.py` | `if grams % 1000 > 0:` | `if whole % 1000 > 0:` |
| shipping-d4 | D4 | `src/zones.py` | `return COUNTRIES.get(country, "world")` | `return COUNTRIES.get(postcode, "world")` |
| snapshots-d1 | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = existing[-1] - 1 if existing else 1` |
| snapshots-d1b | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = existing[0] + 1 if existing else 1` |
| snapshots-d1c | D1 | `src/snapshots.py` | `return number` | (line deleted) |
| snapshots-d1d | D1 | `src/snapshots.py` | `existing = list_snapshots(folder)` | (line deleted) |
| snapshots-d1e | D1 | `src/snapshots.py` | `elif number < 0:` | (line deleted) |
| snapshots-d1f | D1 | `src/snapshots.py` | `path = os.path.join(folder, _name_for(number))` | (line deleted) |
| snapshots-d1g | D1 | `src/snapshots.py` | `number = existing[-1] + 1 if existing else 1` | `number = tmp[-1] + 1 if existing else 1` |
| snapshots-d1h | D1 | `src/snapshots.py` | `return number` | `return folder` |
| tablefmt-d1 | D1 | `src/cells.py` | `if len(text) <= width:` | `if len(width) <= width:` |
| tablefmt-d1b | D1 | `src/cells.py` | `if is_number(value):` | (line deleted) |
| tablefmt-d1c | D1 | `src/columns.py` | `longest = max(longest, len(row[i]))` | `longest = max(longest, len(row[headers]))` |
| tablefmt-d2 | D2 | `src/render.py` | `cells = []` | (line deleted) |
| tablefmt-d2b | D2 | `src/render.py` | `if aligns[0] == "left":` | `if aligns[0] != "left":` |
| tablefmt-d2c | D2 | `src/render.py` | `return " | ".join(cells).rstrip()` | `return` |
| tablefmt-d2d | D2 | `src/cells.py` | `return isinstance(value, (int, float))` | (line deleted) |
| tablefmt-d3 | D3 | `src/columns.py` | `widths.append(min(longest, cap))` | `widths.append(min(longest, widths))` |
| tablefmt-d3 | D3 | `src/render.py` | `if totals:` | `if texts:` |
| tablefmt-d4 | D4 | `src/cells.py` | `if len(text) <= width:` | `if len(width) <= width:` |
| tablefmt-d4 | D4 | `src/columns.py` | `longest = max(longest, len(row[i]))` | `longest = max(longest, len(row[headers]))` |
| tablefmt-d4 | D4 | `src/render.py` | `cells = []` | (line deleted) |
| timespan-d1 | D1 | `src/timespan.py` | `total = 0` | `total = 1` |
| timespan-d1b | D1 | `src/timespan.py` | `if len(parts) == max_units:` | `if len(parts) != max_units:` |
| timespan-d1c | D1 | `src/timespan.py` | `total += amount * UNIT_SECONDS[unit]` | (line deleted) |
| timespan-d1d | D1 | `src/timespan.py` | `parts = []` | `max_units = []` |
| timespan-d2 | D2 | `src/timespan.py` | `number += ch` | `number -= ch` |
| timespan-d2b | D2 | `src/timespan.py` | `if number:` | (line deleted) |
| timespan-d2c | D2 | `src/timespan.py` | `number = ""` | `ch = ""` |
| timespan-d2d | D2 | `src/timespan.py` | `if number:` | `if ch:` |
| wallet-d1 | D1 | `src/bank.py` | `charged.append(name)` | `account.append(name)` |
| wallet-d1b | D1 | `src/bank.py` | `for name in sorted(self.accounts):` | `for fee in sorted(self.accounts):` |
| wallet-d1c | D1 | `src/bank.py` | `return self.get(name).history.last(count)` | `return` |
| wallet-d2 | D2 | `src/history.py` | `return list(self.entries[-count:])` | (line deleted) |
| wallet-d2b | D2 | `src/bank.py` | `return self.accounts[name]` | (line deleted) |
| wallet-d2c | D2 | `src/history.py` | `return sum(delta for name, delta, _ in self.entries if name == account)` | `return sum(delta for name, delta, _ in self.entries if name != account)` |
| wallet-d2d | D2 | `src/account.py` | `return self.balance() + self.overdraft` | `return` |
| wallet-d3 | D3 | `src/account.py` | `if amount <= 0:` | `if memo <= 0:` |
| wallet-d3 | D3 | `src/bank.py` | `target.deposit(amount, "transfer from " + src)` | `target.deposit(amount, "transfer from " - src)` |
| wallet-d4 | D4 | `src/account.py` | `if amount > self.available():` | (line deleted) |
| wallet-d4 | D4 | `src/bank.py` | `charged.append(name)` | `account.append(name)` |
| wallet-d4 | D4 | `src/history.py` | `return list(self.entries[-count:])` | (line deleted) |
| workdays-d1 | D1 | `src/workdays.py` | `current += timedelta(days=step)` | `current -= timedelta(days=step)` |
| workdays-d1b | D1 | `src/workdays.py` | `count += 1` | `count -= 1` |
| workdays-d1c | D1 | `src/workdays.py` | `return date(year, month, min(day.day, last))` | `return date(year, month, max(day.day, last))` |
| workdays-d2 | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | `return (date(year, month + 1, 1) - date(month, year, 1)).days` |
| workdays-d2b | D2 | `src/workdays.py` | `if month == 12:` | `if month != 12:` |
| workdays-d2c | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | `return (date(year, month - 1, 1) - date(year, month, 1)).days` |
| workdays-d2d | D2 | `src/workdays.py` | `return (date(year, month + 1, 1) - date(year, month, 1)).days` | (line deleted) |
| workdays-d2e | D2 | `src/workdays.py` | `return day.weekday() not in WEEKEND and day not in holidays` | `return day.weekday() not in WEEKEND or day not in holidays` |

The first 45 (listed in [`bench-45.txt`](bench-45.txt)) are the original set that Stages 1 to 5 were measured on;
`python run.py --tasks tasks/bench-45.txt` runs only them. The other 74 were added in Stage 7: three more from each
of the 9 original projects, and 8 from each of 6 new, larger projects (booking, gradebook, router, shipping,
tablefmt, wallet), with three new kinds of bug: a `return` that lost its value, the wrong variable, and a dropped
copy. The 6 D4 tasks (one per three-file project, `make_tasks.py --d4`) came later, to keep the set ahead of
the agent; [`bench-119.txt`](bench-119.txt) lists the 119 before them.

## Held out

These 27 tasks (listed in [`held_out.txt`](held_out.txt)) are never read while designing a stage: their traces stay
unopened and no prompt or tool is tuned on them. They are graded in every run, so a stage that only works on the
tasks it was tuned on shows up as a gap between the two groups (`report.py` prints pass@1 for each). They are one
task of each original project, and every task of two whole new projects (router and wallet), so that no stage can
be tuned on code it is tested on.

`inventory-d2b`, `invoice-d2b`, `kvconfig-d1`, `numtools-d1c`, `recent-d2b`, `ringlog-d1e`, `snapshots-d1d`, `timespan-d1c`, `workdays-d2b`, `router-d1`, `router-d1b`, `router-d1c`, `router-d2`, `router-d2b`, `router-d2c`, `router-d2d`, `router-d3`, `wallet-d1`, `wallet-d1b`, `wallet-d1c`, `wallet-d2`, `wallet-d2b`, `wallet-d2c`, `wallet-d2d`, `wallet-d3`, `router-d4`, `wallet-d4`
