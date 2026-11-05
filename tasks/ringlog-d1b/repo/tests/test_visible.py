from ringlog import RingLog


def test_entries_kept_in_order():
    """Appending a, b, c to a log of capacity 5 should list them back as [a, b, c]."""
    log = RingLog(5)
    for item in "abc":
        log.append(item)
    assert log.snapshot() == ["a", "b", "c"]
    assert len(log) == 3


def test_full_log_overwrites_oldest():
    """When a log of capacity 3 receives a fourth entry, the oldest entry should be discarded."""
    log = RingLog(3)
    for item in [1, 2, 3, 4]:
        log.append(item)
    assert log.snapshot() == [2, 3, 4]


def test_popleft_returns_oldest():
    """Popping from the left should return entries oldest-first and shrink the log."""
    log = RingLog(4)
    for item in [10, 20, 30]:
        log.append(item)
    assert log.popleft() == 10
    assert log.popleft() == 20
    assert len(log) == 1


def test_tail_returns_newest():
    """Asking for the last 2 entries of [1, 2, 3] should give [2, 3]."""
    log = RingLog(5)
    for item in [1, 2, 3]:
        log.append(item)
    assert log.tail(2) == [2, 3]
