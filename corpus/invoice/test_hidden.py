import pytest

from invoice import Invoice
from money import format_cents, percent_of, split_evenly, to_cents


def test_short_and_bare_amounts():
    assert to_cents("12.5") == 1250
    assert to_cents(".99") == 99
    assert to_cents("7") == 700
    assert to_cents(" -3.10 ") == -310


def test_bad_amounts_rejected():
    for text in ["1.234", "abc", "", "1.2.3"]:
        with pytest.raises(ValueError):
            to_cents(text)


def test_negative_formatting():
    assert format_cents(-5) == "-0.05"
    assert format_cents(123456) == "1234.56"


def test_percent_rounds_half_away_from_zero():
    assert percent_of(1, 5000) == 1
    assert percent_of(3, 5000) == 2
    assert percent_of(-3, 5000) == -2
    assert percent_of(10, 1234) == 1


def test_full_discount_means_zero_tax():
    inv = Invoice(tax_bp=2500)
    inv.add_line("gift", "40.00")
    inv.set_discount(10000)
    assert inv.total() == 0


def test_invalid_quantity_and_discount():
    inv = Invoice()
    with pytest.raises(ValueError):
        inv.add_line("x", "1.00", 0)
    with pytest.raises(ValueError):
        inv.set_discount(10001)


def test_split_puts_extra_cents_first():
    assert split_evenly(1000, 3) == [334, 333, 333]
    assert split_evenly(5, 5) == [1, 1, 1, 1, 1]
    with pytest.raises(ValueError):
        split_evenly(100, 0)


def test_invoice_split_formatted():
    inv = Invoice(tax_bp=500)
    inv.add_line("meal", "19.99", 3)
    assert inv.total() == 6297
    assert inv.split(2) == ["31.49", "31.48"]


def test_rounded_tax_on_odd_amount():
    inv = Invoice(tax_bp=825)
    inv.add_line("cable", "9.99")
    inv.set_discount(1500)
    assert inv.discount() == 150
    assert inv.tax() == 70
    assert inv.summary()["total"] == "9.19"
