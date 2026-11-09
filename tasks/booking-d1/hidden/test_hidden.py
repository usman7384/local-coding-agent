import pytest

from planner import Planner
from rooms import Room
from slots import format_time, gaps, merge, overlaps, parse_time


def make():
    return Planner([Room("big", 10), Room("small", 4), Room("mid", 6)])


def test_parse_and_format_round_trip():
    assert parse_time("00:05") == 5
    assert parse_time("17:00") == 1020
    assert format_time(570) == "09:30"
    assert format_time(5) == "00:05"
    assert format_time(1020) == "17:00"


def test_overlaps_half_open():
    assert overlaps((0, 10), (5, 15))
    assert overlaps((5, 15), (0, 10))
    assert overlaps((0, 10), (2, 3))
    assert not overlaps((0, 10), (10, 20))
    assert not overlaps((10, 20), (0, 10))
    assert not overlaps((0, 5), (8, 9))


def test_merge_touching_nested_and_empty():
    assert merge([]) == []
    assert merge([(0, 10), (10, 20)]) == [(0, 20)]
    assert merge([(0, 100), (10, 20)]) == [(0, 100)]
    assert merge([(30, 40), (0, 10)]) == [(0, 10), (30, 40)]
    assert merge([(0, 10), (5, 8), (7, 30)]) == [(0, 30)]


def test_gaps():
    assert gaps([], 0, 100) == [(0, 100)]
    assert gaps([(10, 20), (15, 30)], 0, 100) == [(0, 10), (30, 100)]
    assert gaps([(0, 40)], 0, 100) == [(40, 100)]
    assert gaps([(60, 100)], 0, 100) == [(0, 60)]
    assert gaps([(50, 150)], 0, 100) == [(0, 50)]
    assert gaps([(0, 100)], 0, 100) == []


def test_room_is_free_and_adjacent_bookings():
    room = Room("r", 3)
    room.book(100, 200, "a")
    assert room.is_free(200, 300)
    assert room.is_free(50, 100)
    assert not room.is_free(150, 250)
    assert not room.is_free(0, 500)
    room.book(200, 300, "b")
    assert room.busy() == [(100, 200), (200, 300)]


def test_room_book_rejects_bad_input():
    room = Room("r", 3)
    room.book(100, 200, "a")
    with pytest.raises(ValueError):
        room.book(150, 250, "b")
    with pytest.raises(ValueError):
        room.book(300, 300, "c")
    with pytest.raises(ValueError):
        room.book(400, 300, "d")
    assert room.bookings == [(100, 200, "a")]


def test_room_cancel_and_minutes():
    room = Room("r", 3)
    room.book(100, 160, "a")
    room.book(200, 230, "b")
    assert room.booked_minutes() == 90
    assert room.cancel("a") is True
    assert room.cancel("a") is False
    assert room.booked_minutes() == 30
    assert room.busy() == [(200, 230)]


def test_book_falls_back_to_next_room():
    planner = make()
    assert planner.book(3, 600, 660, "a") == "small"
    assert planner.book(3, 630, 690, "b") == "mid"
    assert planner.book(3, 640, 700, "c") == "big"
    with pytest.raises(ValueError):
        planner.book(3, 650, 700, "d")


def test_book_group_too_large():
    planner = make()
    assert planner.book(4, 600, 660, "a") == "small"
    assert planner.book(10, 600, 660, "b") == "big"
    with pytest.raises(ValueError):
        planner.book(11, 700, 760, "c")


def test_failed_book_leaves_no_trace():
    planner = make()
    with pytest.raises(ValueError):
        planner.book(20, 600, 660, "a")
    assert planner.free_slots("big") == [(540, 1020)]
    assert planner.cancel("a") is False


def test_free_slots_multiple_and_full_day():
    planner = make()
    assert planner.free_slots("mid") == [(540, 1020)]
    planner.book(5, 540, 600, "a")
    planner.book(5, 720, 780, "b")
    assert planner.free_slots("mid") == [(600, 720), (780, 1020)]
    planner.book(5, 600, 720, "c")
    planner.book(5, 780, 1020, "d")
    assert planner.free_slots("mid") == []
    assert planner.utilisation("mid") == 100


def test_find_unknown_room_and_cancel_unknown():
    planner = make()
    assert planner.find("mid").capacity == 6
    with pytest.raises(KeyError):
        planner.find("none")
    with pytest.raises(KeyError):
        planner.free_slots("none")
    assert planner.cancel("zzz") is False


def test_utilisation_rounds_down_and_cancel_updates():
    planner = make()
    assert planner.utilisation("small") == 0
    planner.book(2, 540, 580, "a")
    assert planner.utilisation("small") == 8
    planner.book(2, 600, 660, "b")
    assert planner.utilisation("small") == 20
    assert planner.cancel("b") is True
    assert planner.utilisation("small") == 8
