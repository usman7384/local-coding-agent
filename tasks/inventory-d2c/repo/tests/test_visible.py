import pytest

from stock import StockKeeper


def test_restock_increases_on_hand():
    """Restocking 5 and then 3 units of an item should leave 8 on hand."""
    keeper = StockKeeper()
    keeper.restock("bolt", 5)
    keeper.restock("bolt", 3)
    assert keeper.on_hand("bolt") == 8


def test_reserve_lowers_available_only():
    """Reserving 4 of 10 units should leave 6 unclaimed while 10 stay on hand."""
    keeper = StockKeeper()
    keeper.restock("nut", 10)
    keeper.reserve("nut", 4)
    assert keeper.available("nut") == 6
    assert keeper.on_hand("nut") == 10


def test_shipping_reserved_units():
    """Shipping 3 reserved units out of 10 should leave 7 on hand and 7 unclaimed."""
    keeper = StockKeeper()
    keeper.restock("gear", 10)
    keeper.reserve("gear", 3)
    keeper.ship("gear", 3)
    assert keeper.on_hand("gear") == 7
    assert keeper.available("gear") == 7


def test_over_reservation_rejected():
    """Reserving more units than are free should raise ValueError."""
    keeper = StockKeeper()
    keeper.restock("pin", 2)
    with pytest.raises(ValueError):
        keeper.reserve("pin", 3)
