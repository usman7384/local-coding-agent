from cells import cell_text, format_number, is_number, one_line, truncate
from columns import column_totals, column_widths, infer_alignments, pad_cell
from render import format_line, render, rule, totals_row


def test_truncate_boundaries():
    assert truncate("abcdef", 6) == "abcdef"
    assert truncate("abcdefg", 6) == "abcde…"
    assert truncate("ab", 2) == "ab"
    assert truncate("abc", 1) == "…"


def test_is_number():
    assert is_number(3) is True
    assert is_number(2.5) is True
    assert is_number(True) is False
    assert is_number("3") is False
    assert is_number(None) is False


def test_format_number():
    assert format_number(2, 2) == "2.00"
    assert format_number(2.345, 1) == "2.3"
    assert format_number(-1.5, 0) == "-2"


def test_one_line():
    assert one_line("a\nb  c") == "a b c"
    assert one_line(" x ") == "x"


def test_cell_text_more():
    assert cell_text("hello world", max_width=5) == "hell…"
    assert cell_text(7, decimals=0) == "7"
    assert cell_text(True) == "True"
    assert cell_text("a\nb") == "a b"
    assert cell_text(1234.5, max_width=3) == "1234.50"


def test_widths_header_longer_and_empty():
    assert column_widths(["header"], [["a"]], 20) == [6]
    assert column_widths(["h"], [], 20) == [1]
    assert column_widths(["a", "b"], [["xx", "y"]], 20) == [2, 1]


def test_alignments_edge_cases():
    assert infer_alignments(["a"], [[None], [None]]) == ["left"]
    assert infer_alignments(["a"], []) == ["left"]
    assert infer_alignments(["a"], [[1], ["x"]]) == ["left"]
    assert infer_alignments(["a"], [[1.5], [2]]) == ["right"]
    assert infer_alignments(["a"], [[True]]) == ["left"]


def test_pad_cell():
    assert pad_cell("ab", 4, "left") == "ab  "
    assert pad_cell("ab", 4, "right") == "  ab"
    assert pad_cell("abcd", 2, "left") == "abcd"


def test_column_totals():
    rows = [["a", 1, None], ["b", 2.5, 3]]
    assert column_totals(rows, ["left", "right", "right"]) == [None, 3.5, 3]
    assert column_totals([], ["right"]) == [0]
    assert column_totals([["a", 1]], ["left", "left"]) == [None, None]


def test_format_line_and_rule():
    assert format_line(["a", "b"], [3, 2], ["left", "right"]) == "a   |  b"
    assert format_line(["a", ""], [3, 2], ["left", "left"]) == "a   |"
    assert rule([2, 3]) == "---+----"
    assert rule([1]) == "-"


def test_totals_row_label():
    assert totals_row([["a", 1], ["b", 2]], ["left", "right"]) == ["Total", 3]
    assert totals_row([[1, 2], [3, 4]], ["right", "right"]) == [4, 6]


def test_render_missing_and_truncation():
    lines = render(["name", "qty"], [["abcdefghij", None], ["z", 1]], decimals=1, max_width=6)
    assert lines == [
        "name   | qty",
        "-------+----",
        "abcde… |",
        "z      | 1.0",
    ]


def test_render_long_header_and_empty():
    assert render(["abcdefghij"], [["x"]], max_width=5) == ["abcd…", "-----", "x"]
    assert render(["a", "b"], []) == ["a | b", "--+--"]
    assert render(["a", "b"], [], totals=True)[-1] == "Total |"
