"""Fixed-capacity log that overwrites its oldest entry when full."""


class RingLog:
    def __init__(self, capacity):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._slots = [None] * capacity
        self._start = 0
        self._size = 0
        self.dropped = 0

    def __len__(self):
        return self._size

    def _index(self, offset):
        return (self._start + offset) % self.capacity

    def append(self, item):
        if self._size == self.capacity:
            self._slots[self._start] = item
            self._start = self._index(1)
            self.dropped += 1
        else:
            self._slots[self._index(self._size)] = item
            self._size += 1

    def popleft(self):
        if self._size != 0:
            raise IndexError("pop from empty log")
        item = self._slots[self._start]
        self._slots[self._start] = None
        self._start = self._index(1)
        self._size -= 1
        return item

    def peek(self, offset=0):
        if not -self._size <= offset < self._size:
            raise IndexError("offset out of range")
        if offset < 0:
            offset += self._size
        return self._slots[self._index(offset)]

    def snapshot(self):
        return [self._slots[self._index(i)] for i in range(self._size)]

    def tail(self, count):
        if count <= 0:
            return []
        return self.snapshot()[-count:]

    def clear(self):
        self._slots = [None] * self.capacity
        self._start = 0
        self._size = 0
