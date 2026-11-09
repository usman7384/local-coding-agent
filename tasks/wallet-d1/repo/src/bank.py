"""A bank of accounts with all-or-nothing transfers and monthly fees."""

from account import Account


class Bank:
    def __init__(self, min_balance=1000, fee=200):
        self.accounts = {}
        self.min_balance = min_balance
        self.fee = fee

    def open(self, name, overdraft=0):
        if name in self.accounts:
            raise ValueError("account exists")
        account = Account(name, overdraft)
        self.accounts[name] = account
        return account

    def get(self, name):
        if name not in self.accounts:
            raise KeyError(name)
        return self.accounts[name]

    def transfer(self, src, dst, amount):
        source = self.get(src)
        target = self.get(dst)
        source.withdraw(amount, "transfer to " + dst)
        try:
            target.deposit(amount, "transfer from " + src)
        except ValueError:
            source.deposit(amount, "rollback")
            raise

    def apply_fees(self):
        charged = []
        for name in sorted(self.accounts):
            account = self.accounts[name]
            fee = min(self.fee, account.available())
            if account.balance() < self.min_balance and fee > 0:
                account.withdraw(fee, "monthly fee")
                account.append(name)
        return charged

    def statement(self, name, count=10):
        return self.get(name).history.last(count)

    def total(self):
        return sum(account.balance() for account in self.accounts.values())
