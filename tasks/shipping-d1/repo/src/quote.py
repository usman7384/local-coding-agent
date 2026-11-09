"""Combine parcels, zone and rules into a shipping quote in cents."""

from rates import price_for
from zones import apply_zone, zone_for

VOLUME_DIVISOR = 5000
OVERSIZE_CM = 100
OVERSIZE_FEE = 1500
FREE_ABOVE = 10000


def volumetric_grams(length, width, height):
    return length * width * height * 1000 // VOLUME_DIVISOR


def billable_grams(grams, length, width, height):
    return max(grams, volumetric_grams(length, width, height))


def surcharge(length, width, height):
    if max(length, width, height) > OVERSIZE_CM:
        return OVERSIZE_FEE
    return 0


class Quote:
    def __init__(self, country, postcode):
        self.zone = zone_for(country, postcode)
        self.parcels = []

    def add_parcel(self, grams, length, width, height):
        if grams <= 0:
            raise ValueError("parcel weight must be positive")
        self.parcels.append((grams, length, width, height))

    def parcel_cost(self, parcel):
        grams, length, width, height = parcel
        billable = billable_grams(grams, length, width, height)
        zoned = apply_zone(price_for(billable), self.zone)
        return zoned + surcharge(length, width, height)

    def subtotal(self):
        total = 0
        for parcel in self.parcels:
            total += self.parcel_cost(parcel)
        return total

    def total(self, order_value=0):
        if order_value >= FREE_ABOVE:
            return
        return self.subtotal()
