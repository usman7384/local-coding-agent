"""Append-only movement ledger used by the stock keeper."""


class Ledger:
    def __init__(self):
        self.entries = []

    def record(self, sku, delta, reason):
        if delta == 0:
            raise ValueError("zero movement")
        self.entries.append((sku, delta, reason))

    def balance(self, sku):
        return sum(delta for item, delta, _ in self.entries if item == sku)

    def history(self, sku, reason=None):
        return [
            delta
            for item, delta, why in self.entries
            if item == sku and (reason is None or why == reason)
        ]
