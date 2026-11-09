import pytest

from planner import Planner
from rooms import Room
from slots import merge, parse_time


def make():
    return Planner([Room("big", 10), Room("small", 4), Room("mid", 6)])


def test_parse_time():
    """The time 09:30 should be read as 570 minutes since midnight."""
    assert parse_time("09:30") == 570


def test_merge_intervals():
    """Merging (60, 120), (100, 180) and (200, 240) should give (60, 180) and (200, 240)."""
    assert merge([(200, 240), (60, 120), (100, 180)]) == [(60, 180), (200, 240)]


def test_smallest_fitting_room():
    """A group of 5 should be booked into the 6-seat room rather than the 10-seat one."""
    planner = make()
    assert planner.book(5, 600, 660, "a") == "mid"


def test_free_slots_around_booking():
    """With 10:00-11:00 booked, the room should be free 09:00-10:00 and 11:00-17:00."""
    planner = make()
    planner.book(2, 600, 660, "a")
    assert planner.free_slots("small") == [(540, 600), (660, 1020)]


def test_cancel_frees_room():
    """Cancelling a booking should make its time slot bookable again."""
    planner = make()
    planner.book(2, 600, 660, "a")
    assert planner.cancel("a") is True
    assert planner.book(2, 600, 660, "b") == "small"


def test_utilisation_percent():
    """Booking 2 hours of the 8 hour day should give a utilisation of 25 percent."""
    planner = make()
    planner.book(2, 600, 720, "a")
    assert planner.utilisation("small") == 25
