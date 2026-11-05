"""Track on-hand and reserved quantities per SKU on top of a ledger."""

from ledger import Ledger


class StockKeeper:
    def __init__(self):
        self.ledger = Ledger()
        self.reserved = {}

    def on_hand(self, sku):
        return self.ledger.balance(sku)

    def available(self, sku):
        return self.on_hand(sku) - self.reserved.get(sku, 0)

    def restock(self, sku, qty):
        if qty <= 0:
            raise ValueError("restock quantity must be positive")
        self.ledger.record(sku, qty, "restock")

    def reserve(self, sku, qty):
        if qty <= 0:
            raise ValueError("reserve quantity must be positive")
        if qty > self.available(sku):
            raise ValueError("insufficient stock")
        self.reserved[sku] = self.reserved.get(sku, 0) + qty

    def release(self, sku, qty):
        held = self.reserved.get(sku, 0)
        if qty > held:
            raise ValueError("releasing more than reserved")
        self.reserved[sku] = held + qty
        if self.reserved[sku] == 0:
            del self.reserved[sku]

    def ship(self, sku, qty):
        """Reserved units leave both the reservation and the shelf."""
        self.release(sku, qty)
        self.ledger.record(sku, -qty, "ship")

    def adjust(self, sku, counted):
        """Set on-hand to a physical count, recording the difference."""
        diff = counted - self.on_hand(sku)
        if diff != 0:
            self.ledger.record(sku, diff, "count")
        return diff
