import pytest

from recent import RecentCache


def test_evict_callback_receives_pair():
    seen = []
    cache = RecentCache(1, on_evict=lambda k, v: seen.append((k, v)))
    cache.put("a", 1)
    cache.put("b", 2)
    assert seen == [("a", 1)]


def test_expired_entry_is_a_miss():
    cache = RecentCache(2, max_age=10)
    cache.put("k", "v", now=100)
    assert cache.get("k", now=105) == "v"
    assert cache.get("k", "gone", now=115) == "gone"
    assert cache.misses == 1 and cache.keys() == []


def test_expiry_boundary_is_inclusive():
    cache = RecentCache(2, max_age=5)
    cache.put("k", 1, now=0)
    assert cache.get("k", now=4) == 1
    assert cache.get("k", now=5) is None


def test_update_existing_key_does_not_evict():
    evicted = []
    cache = RecentCache(2, on_evict=lambda k, v: evicted.append(k))
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 3)
    assert evicted == []
    assert cache.get("a") == 3
    assert cache.keys() == ["b", "a"]


def test_peek_does_not_touch():
    cache = RecentCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.peek("a") == 1
    cache.put("c", 3)
    assert cache.peek("a", "none") == "none"
    assert (cache.hits, cache.misses) == (0, 0)


def test_keys_oldest_first():
    cache = RecentCache(3)
    for key in "xyz":
        cache.put(key, key)
    assert cache.keys() == ["x", "y", "z"]


def test_put_refreshes_timestamp():
    cache = RecentCache(2, max_age=10)
    cache.put("k", 1, now=0)
    cache.put("k", 2, now=8)
    assert cache.get("k", now=15) == 2


def test_invalid_capacity():
    with pytest.raises(ValueError):
        RecentCache(0)
