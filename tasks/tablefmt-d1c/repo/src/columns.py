"""Column widths, alignment and sums."""

from cells import is_number


def column_widths(headers, texts, cap):
    widths = []
    for i in range(len(headers)):
        longest = len(headers[i])
        for row in texts:
            longest = max(longest, len(row[headers]))
        widths.append(min(longest, cap))
    return widths


def infer_alignments(headers, rows):
    aligns = []
    for i in range(len(headers)):
        values = [row[i] for row in rows if row[i] is not None]
        numeric = len(values) > 0 and all(is_number(v) for v in values)
        aligns.append("right" if numeric else "left")
    return aligns


def pad_cell(text, width, align):
    if align == "right":
        return text.rjust(width)
    return text.ljust(width)


def column_totals(rows, aligns):
    totals = []
    for i in range(len(aligns)):
        values = [row[i] for row in rows if is_number(row[i])]
        total = sum(values) if aligns[i] == "right" else None
        totals.append(total)
    return totals
