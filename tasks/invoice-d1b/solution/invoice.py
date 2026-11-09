"""An invoice of priced lines with an optional discount and tax."""

from money import format_cents, percent_of, split_evenly, to_cents


class Invoice:
    def __init__(self, tax_bp=0):
        self.tax_bp = tax_bp
        self.discount_bp = 0
        self.lines = []

    def add_line(self, label, unit_price, quantity=1):
        if quantity < 1:
            raise ValueError("quantity must be at least 1")
        self.lines.append((label, to_cents(unit_price), quantity))

    def set_discount(self, basis_points):
        if not 0 <= basis_points <= 10000:
            raise ValueError("discount out of range")
        self.discount_bp = basis_points

    def subtotal(self):
        return sum(price * quantity for _, price, quantity in self.lines)

    def discount(self):
        return percent_of(self.subtotal(), self.discount_bp)

    def tax(self):
        """Tax is charged on the subtotal after the discount."""
        return percent_of(self.subtotal() - self.discount(), self.tax_bp)

    def total(self):
        return self.subtotal() - self.discount() + self.tax()

    def summary(self):
        return {
            "subtotal": format_cents(self.subtotal()),
            "discount": format_cents(self.discount()),
            "tax": format_cents(self.tax()),
            "total": format_cents(self.total()),
        }

    def split(self, people):
        return [format_cents(part) for part in split_evenly(self.total(), people)]
