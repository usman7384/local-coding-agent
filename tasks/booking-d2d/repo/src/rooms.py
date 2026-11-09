"""A meeting room that keeps its own list of bookings."""

from slots import overlaps


class Room:
    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity
        self.bookings = []

    def is_free(self, start, end):
        for b_start, b_end, _ in self.bookings:
            if overlaps((start, end), (b_start, b_end)):
                return False
        return True

    def book(self, start, end, booking_id):
        if end <= start:
            raise ValueError("empty booking")
        if not self.is_free(start, end):
            raise ValueError("room is busy")
        self.bookings.append((start, end, booking_id))

    def cancel(self, booking_id):
        for item in self.bookings:
            if item[2] == booking_id:
                self.bookings.remove(item)
                return True
        return False

    def busy(self):
        return [(start, end) for start, end, _ in self.bookings]

    def booked_minutes(self):
        total = 0
        for start, end, _ in self.bookings:
            total += end - start
