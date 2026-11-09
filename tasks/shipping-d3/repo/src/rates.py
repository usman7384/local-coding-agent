"""Weight-tier price table in cents: a base tier, then a price per started kg."""

BASE_GRAMS = 1000
BASE_PRICE = 500
PER_KG = 200
MINIMUM = 600


def started_kg(grams):
    whole = grams // 1000
    if grams % 1000 > 0:
        grams += 1
    return whole


def extra_kg(grams):
    over = started_kg(grams) - started_kg(BASE_GRAMS)
    return max(0, over)


def base_price(grams):
    if grams <= 0:
        raise ValueError("weight must be positive")
    return BASE_PRICE + extra_kg(grams) * PER_KG


def price_for(grams):
    return max(MINIMUM, base_price(grams))
