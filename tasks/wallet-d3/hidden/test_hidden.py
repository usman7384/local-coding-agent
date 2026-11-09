import pytest

from bank import Bank
from history import History


def test_history_balance_per_account():
    h = History()
    h.add("a", 500, "x")
    h.add("b", 70, "y")
    h.add("a", -200, "z")
    assert h.balance("a") == 300
    assert h.balance("b") == 70
    assert h.balance("c") == 0


def test_history_zero_entry_rejected():
    h = History()
    with pytest.raises(ValueError):
        h.add("a", 0, "x")
    assert h.entries == []


def test_history_last_edges():
    h = History()
    for n in (1, 2, 3):
        h.add("a", n, "m")
    assert h.last(0) == []
    assert h.last(-1) == []
    assert [e[1] for e in h.last(1)] == [3]
    assert len(h.last(9)) == 3


def test_history_copies():
    h = History()
    h.add("a", 5, "m")
    h.all().append(("a", 9, "evil"))
    h.last(1).append(("a", 9, "evil"))
    assert h.entries == [("a", 5, "m")]
    assert h.all() == [("a", 5, "m")]


def test_amounts_must_be_positive():
    account = Bank().open("a", overdraft=100)
    with pytest.raises(ValueError):
        account.deposit(0)
    with pytest.raises(ValueError):
        account.deposit(-5)
    with pytest.raises(ValueError):
        account.withdraw(0)
    with pytest.raises(ValueError):
        account.withdraw(-5)
    assert account.balance() == 0


def test_withdraw_exactly_to_limit_and_memo():
    account = Bank().open("a", overdraft=300)
    account.deposit(200, "pay")
    account.withdraw(500, "rent")
    assert account.balance() == -300
    assert account.available() == 0
    assert account.history.all() == [("a", 200, "pay"), ("a", -500, "rent")]


def test_frozen_blocks_changes_and_thaws():
    account = Bank().open("a")
    account.deposit(100)
    account.freeze()
    with pytest.raises(ValueError):
        account.deposit(50)
    with pytest.raises(ValueError):
        account.withdraw(10)
    assert account.balance() == 100
    account.freeze(False)
    account.deposit(50)
    assert account.balance() == 150


def test_open_and_get():
    bank = Bank()
    first = bank.open("a", 400)
    assert bank.get("a") is first
    assert first.overdraft == 400
    assert first.balance() == 0
    with pytest.raises(ValueError):
        bank.open("a")
    with pytest.raises(KeyError):
        bank.get("zzz")


def test_transfer_rejects_bad_requests():
    bank = Bank()
    bank.open("a").deposit(300)
    bank.open("b")
    with pytest.raises(ValueError):
        bank.transfer("a", "b", 301)
    with pytest.raises(ValueError):
        bank.transfer("a", "b", 0)
    with pytest.raises(KeyError):
        bank.transfer("a", "nobody", 10)
    assert bank.total() == 300
    assert bank.get("a").balance() == 300


def test_rollback_and_transfer_memos():
    bank = Bank()
    bank.open("a").deposit(500)
    bank.open("b").freeze()
    with pytest.raises(ValueError):
        bank.transfer("a", "b", 200)
    memos = [e[2] for e in bank.statement("a")]
    assert memos == ["deposit", "transfer to b", "rollback"]
    assert bank.statement("b") == []
    bank.get("b").freeze(False)
    bank.transfer("a", "b", 100)
    assert bank.statement("b") == [("b", 100, "transfer from a")]


def test_fees_edges():
    bank = Bank(min_balance=1000, fee=200)
    bank.open("exact").deposit(1000)
    bank.open("tiny").deposit(50)
    bank.open("zero")
    bank.open("debt", overdraft=500)
    bank.get("debt").deposit(100)
    assert bank.apply_fees() == ["debt", "tiny"]
    assert bank.get("exact").balance() == 1000
    assert bank.get("tiny").balance() == 0
    assert bank.get("zero").balance() == 0
    assert bank.get("debt").balance() == -100


def test_statement_default_count_and_total():
    bank = Bank()
    account = bank.open("a")
    for n in range(1, 13):
        account.deposit(n)
    lines = bank.statement("a")
    assert len(lines) == 10
    assert lines[0][1] == 3
    assert lines[-1][1] == 12
    assert bank.total() == 78
