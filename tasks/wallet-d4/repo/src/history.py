"""Append-only list of (account, delta, memo) entries, in integer cents."""


class History:
    def __init__(self):
        self.entries = []

    def add(self, account, delta, memo):
        if delta == 0:
            raise ValueError("zero entry")
        self.entries.append((account, delta, memo))

    def balance(self, account):
        return sum(delta for name, delta, _ in self.entries if name == account)

    def last(self, count):
        if count <= 0:
            return []

    def all(self):
        return self.entries.copy()
