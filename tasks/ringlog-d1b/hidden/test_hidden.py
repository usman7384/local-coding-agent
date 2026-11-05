import pytest

from ringlog import RingLog


def test_dropped_counts_overwrites():
    log = RingLog(2)
    for item in range(5):
        log.append(item)
    assert log.dropped == 3
    assert log.snapshot() == [3, 4]


def test_peek_offsets():
    log = RingLog(3)
    for item in "wxyz":
        log.append(item)
    assert log.peek() == "x"
    assert log.peek(2) == "z"
    assert log.peek(-1) == "z"
    assert log.peek(-3) == "x"


def test_peek_out_of_range():
    log = RingLog(3)
    log.append(1)
    for offset in (1, -2):
        with pytest.raises(IndexError):
            log.peek(offset)


def test_pop_empty_raises():
    log = RingLog(2)
    with pytest.raises(IndexError):
        log.popleft()


def test_wraparound_after_pops():
    log = RingLog(3)
    for item in [1, 2, 3]:
        log.append(item)
    log.popleft()
    log.popleft()
    log.append(4)
    log.append(5)
    assert log.snapshot() == [3, 4, 5]
    log.append(6)
    assert log.snapshot() == [4, 5, 6]


def test_clear_then_reuse():
    log = RingLog(2)
    for item in [1, 2, 3]:
        log.append(item)
    log.clear()
    assert len(log) == 0 and log.snapshot() == []
    log.append(9)
    assert log.snapshot() == [9]
    assert log.dropped == 1


def test_tail_edges():
    log = RingLog(4)
    for item in [1, 2]:
        log.append(item)
    assert log.tail(0) == []
    assert log.tail(10) == [1, 2]


def test_capacity_one_and_invalid():
    log = RingLog(1)
    log.append("a")
    log.append("b")
    assert log.snapshot() == ["b"]
    with pytest.raises(ValueError):
        RingLog(0)
