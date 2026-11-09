from quote import Quote


def test_base_tier_price():
    """A 1000 g parcel within the local zone should cost 600 cents."""
    quote = Quote("NL", "1011")
    quote.add_parcel(1000, 10, 10, 10)
    assert quote.subtotal() == 600


def test_started_kg_and_multiple_parcels():
    """Local parcels of 1000 g and 2500 g cost 600 and 900 cents, so 1500 cents together."""
    quote = Quote("NL", "1011")
    quote.add_parcel(1000, 10, 10, 10)
    quote.add_parcel(2500, 10, 10, 10)
    assert quote.subtotal() == 1500


def test_zone_multiplier():
    """A 1000 g parcel sent to Germany should cost 1080 cents."""
    quote = Quote("DE", "10115")
    quote.add_parcel(1000, 10, 10, 10)
    assert quote.subtotal() == 1080


def test_volumetric_weight():
    """A 500 g parcel measuring 40x30x25 cm is billed as 6000 g and costs 1500 cents locally."""
    quote = Quote("NL", "1011")
    quote.add_parcel(500, 40, 30, 25)
    assert quote.subtotal() == 1500


def test_oversize_surcharge():
    """A 1000 g local parcel with a 120 cm side costs 600 plus a 1500 cent fee, so 2100 cents."""
    quote = Quote("NL", "1011")
    quote.add_parcel(1000, 120, 5, 5)
    assert quote.subtotal() == 2100


def test_free_shipping_threshold():
    """An order worth 10000 cents ships free, while one worth 9999 pays the 600 cent quote."""
    quote = Quote("NL", "1011")
    quote.add_parcel(1000, 10, 10, 10)
    assert quote.total(10000) == 0
    assert quote.total(9999) == 600
