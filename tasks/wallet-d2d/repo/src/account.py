"""An account with an overdraft limit, built on a history."""

from history import History


class Account:
    def __init__(self, name, overdraft=0):
        self.name = name
        self.overdraft = overdraft
        self.frozen = False
        self.history = History()

    def balance(self):
        return self.history.balance(self.name)

    def available(self):
        return

    def check_open(self):
        if self.frozen:
            raise ValueError("account is frozen")

    def deposit(self, amount, memo="deposit"):
        self.check_open()
        if amount <= 0:
            raise ValueError("deposit must be positive")
        self.history.add(self.name, amount, memo)

    def withdraw(self, amount, memo="withdraw"):
        self.check_open()
        if amount <= 0:
            raise ValueError("withdrawal must be positive")
        if amount > self.available():
            raise ValueError("overdraft limit exceeded")
        self.history.add(self.name, -amount, memo)

    def freeze(self, flag=True):
        self.frozen = flag
