from report import Gradebook


def test_weighted_final():
    """With homework weighted 40 and exam 60, scoring 17/20 and 45/50 should give a final grade of 88."""
    book = Gradebook({"hw": 40, "exam": 60})
    book.add_score("ann", "hw", 17, 20)
    book.add_score("ann", "exam", 45, 50)
    assert book.final("ann") == 88


def test_empty_category_ignored():
    """A student with only an 80/100 homework score under weights 40 and 60 should still have a final grade of 80."""
    book = Gradebook({"hw": 40, "exam": 60})
    book.add_score("ann", "hw", 80, 100)
    assert book.final("ann") == 80


def test_drop_lowest_score():
    """Dropping the lowest 1 homework score from 50, 90 and 70 out of 100 should give a final grade of 80."""
    book = Gradebook({"hw": 100}, {"hw": 1})
    for points in (50, 90, 70):
        book.add_score("ann", "hw", points, 100)
    assert book.final("ann") == 80


def test_late_penalty_capped():
    """A 90/100 score handed in 2 days late should count as 70, and 5 days late should lose only 30 points and count as 60."""
    book = Gradebook({"hw": 100})
    book.add_score("ann", "hw", 90, 100, days_late=2)
    assert book.final("ann") == 70
    book.add_score("bob", "hw", 90, 100, days_late=5)
    assert book.final("bob") == 60


def test_letter_cutoffs():
    """Final grades of 90, 89 and 59 percent should earn the letters A, B and F."""
    book = Gradebook({"hw": 100})
    book.add_score("a", "hw", 90, 100)
    book.add_score("b", "hw", 89, 100)
    book.add_score("f", "hw", 59, 100)
    assert [book.letter(s) for s in ("a", "b", "f")] == ["A", "B", "F"]


def test_ranking_ties_share_rank():
    """Students finishing with 90, 90 and 80 percent should be ranked 1, 1 and 3, with the tied pair listed alphabetically."""
    book = Gradebook({"hw": 100})
    book.add_score("cy", "hw", 80, 100)
    book.add_score("bob", "hw", 90, 100)
    book.add_score("ann", "hw", 90, 100)
    assert book.ranking() == [("ann", 1), ("bob", 1), ("cy", 3)]
