import pytest

from quote import Quote, billable_grams, surcharge, volumetric_grams
from rates import base_price, extra_kg, price_for, started_kg
from zones import apply_zone, multiplier, zone_for


def test_started_kg_rounds_up():
    assert started_kg(1) == 1
    assert started_kg(1000) == 1
    assert started_kg(1001) == 2
    assert started_kg(3000) == 3


def test_extra_kg_never_negative():
    assert extra_kg(500) == 0
    assert extra_kg(1000) == 0
    assert extra_kg(1001) == 1
    assert extra_kg(4000) == 3


def test_base_price_tiers():
    assert base_price(1) == 500
    assert base_price(1500) == 700
    assert base_price(5000) == 1300
    with pytest.raises(ValueError):
        base_price(0)


def test_price_for_minimum_charge():
    assert price_for(1) == 600
    assert price_for(1000) == 600
    assert price_for(2000) == 700
    assert price_for(5000) == 1300


def test_zone_for_home_prefixes():
    assert zone_for("NL", "1011") == "local"
    assert zone_for("NL", "2011") == "near"
    assert zone_for("NL", "3011") == "near"
    assert zone_for("NL", "9711") == "far"


def test_zone_for_countries():
    assert zone_for("DE", "10115") == "eu"
    assert zone_for("BE", "1000") == "eu"
    assert zone_for("JP", "100") == "world"


def test_multiplier_values():
    assert multiplier("local") == 100
    assert multiplier("near") == 130
    assert multiplier("far") == 160
    assert multiplier("eu") == 180
    assert multiplier("world") == 300


def test_apply_zone_rounds_half_up():
    assert apply_zone(600, "local") == 600
    assert apply_zone(605, "near") == 787
    assert apply_zone(601, "near") == 781
    assert apply_zone(1, "far") == 2
    assert apply_zone(900, "world") == 2700


def test_volumetric_and_billable():
    assert volumetric_grams(40, 30, 25) == 6000
    assert volumetric_grams(10, 10, 10) == 200
    assert billable_grams(500, 40, 30, 25) == 6000
    assert billable_grams(9000, 40, 30, 25) == 9000
    assert billable_grams(200, 10, 10, 10) == 200


def test_surcharge_boundary():
    assert surcharge(100, 100, 100) == 0
    assert surcharge(101, 5, 5) == 1500
    assert surcharge(5, 101, 5) == 1500
    assert surcharge(5, 5, 101) == 1500


def test_quote_state_and_validation():
    quote = Quote("FR", "75001")
    assert quote.zone == "eu"
    assert quote.parcels == []
    assert quote.subtotal() == 0
    with pytest.raises(ValueError):
        quote.add_parcel(0, 10, 10, 10)
    assert quote.parcels == []
    quote.add_parcel(1000, 10, 10, 10)
    assert quote.parcels == [(1000, 10, 10, 10)]


def test_totals_with_zone_surcharge_and_free_shipping():
    quote = Quote("US", "90210")
    quote.add_parcel(2000, 120, 10, 10)
    assert quote.parcel_cost(quote.parcels[0]) == 4200
    assert quote.subtotal() == 4200
    assert quote.total() == 4200
    assert quote.total(10001) == 0
    assert quote.total(9999) == 4200
