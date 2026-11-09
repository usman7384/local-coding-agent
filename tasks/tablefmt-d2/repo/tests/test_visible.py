from cells import cell_text, truncate
from columns import column_widths, infer_alignments
from render import render


def test_cell_text_values():
    """A missing value should show as an empty cell and the number 3 with 2 decimals should show as 3.00."""
    assert cell_text(None) == ""
    assert cell_text(3) == "3.00"
    assert cell_text(2.5, decimals=1) == "2.5"


def test_truncate_long_text():
    """Truncating abcdefghij to width 6 should give abcde followed by an ellipsis, while abc stays unchanged."""
    assert truncate("abcdefghij", 6) == "abcde…"
    assert truncate("abc", 6) == "abc"


def test_widths_use_longest_entry():
    """A column should be as wide as its longest header or cell, but never wider than the cap."""
    texts = [["a", "wide text"], ["bbbb", "x"]]
    assert column_widths(["id", "name"], texts, 20) == [4, 9]
    assert column_widths(["id", "name"], texts, 6) == [4, 6]


def test_numeric_columns_align_right():
    """A column holding only numbers (missing values aside) should align right and any column with text should align left."""
    rows = [["ann", 3, "x"], ["bob", None, 4]]
    assert infer_alignments(["n", "q", "t"], rows) == ["left", "right", "left"]


def test_render_basic_table():
    """Rendering name and qty rows should put a dashed rule under the header and right-align the numbers."""
    lines = render(["name", "qty"], [["bolt", 5], ["nut", 12.5]])
    assert lines == [
        "name | qty",
        "-----+------",
        "bolt |  5.00",
        "nut  | 12.50",
    ]


def test_render_totals_row():
    """Rendering with totals should add a Total row under a second rule that sums each numeric column."""
    lines = render(["item", "n"], [["a", 1], ["b", 2]], decimals=0, totals=True)
    assert lines[-1] == "Total | 3"
    assert lines[-2] == "------+--"
