import pytest

from stock import StockKeeper


def test_release_restores_availability():
    keeper = StockKeeper()
    keeper.restock("a", 5)
    keeper.reserve("a", 5)
    assert keeper.available("a") == 0
    keeper.release("a", 2)
    assert keeper.available("a") == 2
    assert keeper.reserved == {"a": 3}


def test_full_release_drops_entry():
    keeper = StockKeeper()
    keeper.restock("a", 5)
    keeper.reserve("a", 2)
    keeper.release("a", 2)
    assert keeper.reserved == {}


def test_release_too_much_rejected():
    keeper = StockKeeper()
    keeper.restock("a", 5)
    keeper.reserve("a", 1)
    with pytest.raises(ValueError):
        keeper.release("a", 2)


def test_ship_unreserved_rejected_and_stock_unchanged():
    keeper = StockKeeper()
    keeper.restock("a", 5)
    with pytest.raises(ValueError):
        keeper.ship("a", 1)
    assert keeper.on_hand("a") == 5


def test_adjust_records_difference():
    keeper = StockKeeper()
    keeper.restock("a", 10)
    assert keeper.adjust("a", 7) == -3
    assert keeper.on_hand("a") == 7
    assert keeper.ledger.history("a", "count") == [-3]


def test_adjust_to_same_count_records_nothing():
    keeper = StockKeeper()
    keeper.restock("a", 4)
    assert keeper.adjust("a", 4) == 0
    assert len(keeper.ledger.entries) == 1


def test_history_by_reason():
    keeper = StockKeeper()
    keeper.restock("a", 4)
    keeper.restock("b", 9)
    keeper.reserve("a", 1)
    keeper.ship("a", 1)
    assert keeper.ledger.history("a") == [4, -1]
    assert keeper.ledger.history("a", "ship") == [-1]


def test_skus_are_independent():
    keeper = StockKeeper()
    keeper.restock("a", 3)
    keeper.restock("b", 1)
    keeper.reserve("a", 3)
    assert keeper.available("b") == 1
    assert keeper.on_hand("missing") == 0


def test_non_positive_quantities_rejected():
    keeper = StockKeeper()
    with pytest.raises(ValueError):
        keeper.restock("a", 0)
    keeper.restock("a", 1)
    with pytest.raises(ValueError):
        keeper.reserve("a", 0)
