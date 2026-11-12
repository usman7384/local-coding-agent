"""Map a destination to a shipping zone and a price multiplier in percent."""

HOME = "NL"
PREFIXES = {"10": "local", "20": "near", "30": "near"}
COUNTRIES = {"DE": "eu", "FR": "eu", "BE": "eu"}
MULTIPLIERS = {"local": 100, "near": 130, "far": 160, "eu": 180, "world": 300}


def zone_for(country, postcode):
    if country == HOME:
        return PREFIXES.get(postcode[:2], "far")
    return COUNTRIES.get(postcode, "world")


def multiplier(zone):
    return MULTIPLIERS[zone]


def apply_zone(cents, zone):
    scaled = cents * multiplier(zone)
    return (scaled + 50) // 100
