from invoice import Invoice


def test_subtotal_sums_lines():
    """Two lines, 2 x 3.50 and 1 x 10.00, should have a subtotal of 1700 cents."""
    inv = Invoice()
    inv.add_line("tea", "3.50", 2)
    inv.add_line("pot", "10.00")
    assert inv.subtotal() == 1700


def test_total_includes_tax():
    """A 20.00 line with 10% tax (1000 basis points) should total 2200 cents."""
    inv = Invoice(tax_bp=1000)
    inv.add_line("lamp", "20.00")
    assert inv.total() == 2200


def test_discount_applied_before_tax():
    """A 100.00 line with a 10% discount and 20% tax should have tax 1800 and total 10800 cents."""
    inv = Invoice(tax_bp=2000)
    inv.add_line("desk", "100.00")
    inv.set_discount(1000)
    assert inv.tax() == 1800
    assert inv.total() == 10800


def test_summary_is_formatted():
    """The summary of a single 5.05 line with no tax should show '5.05' for subtotal and total."""
    inv = Invoice()
    inv.add_line("pen", "5.05")
    summary = inv.summary()
    assert summary["subtotal"] == "5.05"
    assert summary["total"] == "5.05"
    assert summary["tax"] == "0.00"
