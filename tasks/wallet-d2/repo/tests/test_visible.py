from bank import Bank


def test_deposit_and_withdraw():
    """Depositing 5000 cents and then withdrawing 1200 cents should leave a balance of 3800."""
    account = Bank().open("amy")
    account.deposit(5000)
    account.withdraw(1200)
    assert account.balance() == 3800


def test_overdraft_limit():
    """An account with a 1000 cent overdraft and 500 cents may withdraw 1400 but then not 200 more."""
    account = Bank().open("ben", overdraft=1000)
    account.deposit(500)
    account.withdraw(1400)
    assert account.balance() == -900
    try:
        account.withdraw(200)
        assert False
    except ValueError:
        assert account.balance() == -900


def test_transfer_moves_money():
    """Transferring 2500 from an account holding 10000 to one holding 1000 should leave 7500 and 3500."""
    bank = Bank()
    bank.open("a").deposit(10000)
    bank.open("b").deposit(1000)
    bank.transfer("a", "b", 2500)
    assert bank.get("a").balance() == 7500
    assert bank.get("b").balance() == 3500


def test_failed_transfer_is_rolled_back():
    """A transfer of 2000 into a frozen account should fail and leave the sender at 5000."""
    bank = Bank()
    bank.open("a").deposit(5000)
    bank.open("b").freeze()
    try:
        bank.transfer("a", "b", 2000)
        assert False
    except ValueError:
        assert bank.get("a").balance() == 5000
        assert bank.total() == 5000


def test_monthly_fee_below_minimum():
    """With a 1000 minimum and a 200 fee, an account holding 600 drops to 400 and one holding 1500 stays."""
    bank = Bank(min_balance=1000, fee=200)
    bank.open("low").deposit(600)
    bank.open("rich").deposit(1500)
    assert bank.apply_fees() == ["low"]
    assert bank.get("low").balance() == 400
    assert bank.get("rich").balance() == 1500


def test_statement_is_a_copy():
    """Changing a returned statement of the last 2 entries must not change the account history of 3 entries."""
    bank = Bank()
    account = bank.open("amy")
    for amount in (100, 200, 300):
        account.deposit(amount)
    lines = bank.statement("amy", 2)
    assert [line[1] for line in lines] == [200, 300]
    lines.clear()
    assert len(bank.statement("amy")) == 3
