"""Least-recently-used mapping with an explicit logical clock for expiry."""


class RecentCache:
    def __init__(self, capacity, max_age=None, on_evict=None):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.max_age = max_age
        self.on_evict = on_evict
        self._data = {}
        self._order = []
        self.hits = 0
        self.misses = 0

    def _touch(self, key):
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def _expired(self, key, now):
        if self.max_age is None:
            return False
        stored_at = self._data[key][1]
        return now - stored_at >= self.max_age

    def _evict(self, key):
        value, _ = self._data.pop(key)
        self._order.remove(key)
        if self.on_evict is not None:
            self.on_evict(key, value)

    def put(self, key, value, now=0):
        if key not in self._data and len(self._data) >= self.capacity:
            self._evict(self._order[0])
        self._data[key] = (value, now)

    def get(self, key, default=None, now=0):
        if key not in self._data:
            self.misses += 1
            return default
        if self._expired(key, now):
            self._evict(key)
            self.misses += 1
            return default
        self.hits += 1
        self._touch(key)
        return self._data[key][0]

    def peek(self, key, default=None):
        entry = self._data.get(key)
        return default if entry is None else entry[0]

    def keys(self):
        return list(self._order)
