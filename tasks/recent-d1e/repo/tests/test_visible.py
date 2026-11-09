from recent import RecentCache


def test_put_then_get():
    """A value stored under a key should be returned when that key is read back."""
    cache = RecentCache(2)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_least_recent_evicted():
    """With capacity 2, storing a third key should push out the least recently used key."""
    cache = RecentCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2 and cache.get("c") == 3


def test_read_refreshes_recency():
    """Reading a key should mark it as freshly used, so the other key is evicted next."""
    cache = RecentCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.put("c", 3)
    assert cache.keys() == ["a", "c"]


def test_hit_and_miss_counters():
    """Two successful reads and one read of a missing key should count 2 hits and 1 miss."""
    cache = RecentCache(3)
    cache.put("x", 10)
    cache.get("x")
    cache.get("x")
    cache.get("nope")
    assert (cache.hits, cache.misses) == (2, 1)
