import pytest

from report import Gradebook
from scores import average, drop_lowest, late_penalty, percentage
from weights import active_weight, check_weights, weighted_average


def test_percentage_rounding():
    assert percentage(1, 8) == 13
    assert percentage(1, 3) == 33
    assert percentage(2, 3) == 67
    assert percentage(0, 10) == 0
    assert percentage(10, 10) == 100
    assert percentage(12, 10) == 120


def test_average_rounding():
    assert average([85]) == 85
    assert average([80, 81]) == 81
    assert average([80, 80, 81]) == 80
    assert average([70, 90, 100]) == 87


def test_drop_lowest_basic():
    values = [50, 90, 70]
    assert drop_lowest(values, 0) == [50, 70, 90]
    assert drop_lowest(values, 1) == [70, 90]
    assert drop_lowest(values, 2) == [90]
    assert values == [50, 90, 70]


def test_drop_lowest_keeps_one():
    assert drop_lowest([40, 60], 5) == [60]
    assert drop_lowest([40], 1) == [40]
    assert drop_lowest([], 1) == []
    assert drop_lowest([40, 60], -3) == [40, 60]


def test_late_penalty_values():
    assert late_penalty(90, 0) == 90
    assert late_penalty(90, 1) == 80
    assert late_penalty(90, 3) == 60
    assert late_penalty(90, 4) == 60
    assert late_penalty(20, 3) == 0
    assert late_penalty(0, 1) == 0


def test_check_weights():
    weights = {"a": 30, "b": 70}
    assert check_weights(weights) is weights
    with pytest.raises(ValueError):
        check_weights({"a": 30, "b": 60})
    with pytest.raises(ValueError):
        check_weights({"a": 60, "b": 60})


def test_active_weight():
    weights = {"a": 20, "b": 30, "c": 50}
    assert active_weight(weights, {"a": 90, "c": 70}) == 70
    assert active_weight(weights, {}) == 0
    assert active_weight(weights, {"b": 0}) == 30


def test_weighted_average_renormalises():
    weights = {"a": 20, "b": 30, "c": 50}
    assert weighted_average(weights, {"a": 100, "b": 50, "c": 80}) == 75
    assert weighted_average(weights, {"a": 90, "c": 70}) == 76
    assert weighted_average(weights, {"b": 61}) == 61
    assert weighted_average(weights, {}) == 0
    assert weighted_average({"a": 50, "b": 50}, {"a": 80, "b": 81}) == 81


def test_category_percent():
    book = Gradebook({"hw": 50, "exam": 50}, {"hw": 1})
    assert book.category_percent("ann", "hw") is None
    book.add_score("ann", "hw", 0, 10)
    assert book.category_percent("ann", "hw") == 0
    book.add_score("ann", "hw", 7, 10)
    book.add_score("ann", "hw", 9, 10)
    assert book.category_percent("ann", "hw") == 80
    assert book.category_percent("ann", "exam") is None
    assert book.category_percent("bob", "hw") is None


def test_final_and_students_isolated():
    book = Gradebook({"hw": 50, "exam": 50})
    assert book.final("nobody") == 0
    book.add_score("ann", "hw", 10, 10)
    book.add_score("ann", "exam", 5, 10)
    book.add_score("bob", "hw", 1, 10)
    assert book.final("ann") == 75
    assert book.final("bob") == 10


def test_letter_all_bands():
    book = Gradebook({"hw": 100})
    for name, points in (("a", 90), ("b", 80), ("c", 70), ("d", 60), ("e", 59), ("f", 79)):
        book.add_score(name, "hw", points, 100)
    assert [book.letter(s) for s in "abcdef"] == ["A", "B", "C", "D", "F", "C"]


def test_ranking_order_and_bad_weights():
    book = Gradebook({"hw": 100})
    assert book.ranking() == []
    for name, points in (("d", 70), ("c", 90), ("b", 70), ("a", 70)):
        book.add_score(name, "hw", points, 100)
    assert book.ranking() == [("c", 1), ("a", 2), ("b", 2), ("d", 2)]
    with pytest.raises(ValueError):
        Gradebook({"hw": 50})
