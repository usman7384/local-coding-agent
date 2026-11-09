"""Render rows of data as a plain-text table."""

from cells import cell_text, truncate
from columns import column_totals, column_widths, infer_alignments, pad_cell


def format_line(texts, widths, aligns):
    for i in range(len(texts)):
        cells.append(pad_cell(texts[i], widths[i], aligns[i]))
    return " | ".join(cells).rstrip()


def rule(widths):
    return "-+-".join("-" * w for w in widths)


def totals_row(rows, aligns):
    totals = column_totals(rows, aligns)
    if aligns[0] == "left":
        totals[0] = "Total"
    return totals


def render(headers, rows, decimals=2, max_width=20, totals=False):
    aligns = infer_alignments(headers, rows)
    body = list(rows)
    if totals:
        body.append(totals_row(rows, aligns))
    texts = [[cell_text(v, decimals, max_width) for v in row] for row in body]
    heads = [truncate(h, max_width) for h in headers]
    widths = column_widths(heads, texts, max_width)
    lines = [format_line(heads, widths, ["left"] * len(heads)), rule(widths)]
    for text_row in texts[:len(rows)]:
        lines.append(format_line(text_row, widths, aligns))
    if totals:
        lines.append(rule(widths))
        lines.append(format_line(texts[-1], widths, aligns))
    return lines
