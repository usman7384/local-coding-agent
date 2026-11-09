"""Plan bookings across several rooms in a 09:00-17:00 working day."""

from slots import gaps, parse_time

DAY_START = parse_time("09:00")
DAY_END = parse_time("17:00")


class Planner:
    def __init__(self, rooms):
        self.rooms = rooms

    def find(self, name):
        for room in self.rooms:
            if room.name == name:
                return room
        raise KeyError(name)

    def book(self, size, start, end, booking_id):
        """Book the smallest free room that fits the group and return its name."""
        fits = [r for r in self.rooms if r.capacity >= size and r.is_free(start, end)]
        if not fits:
            raise ValueError("no room available")
        room.book(start, end, booking_id)
        return room.name

    def free_slots(self, name):
        return gaps(self.find(name).busy(), DAY_START, DAY_END)

    def cancel(self, booking_id):
        for room in self.rooms:
            if room.cancel(booking_id):
                return True
        return False

    def utilisation(self, name):
        used = self.find(name).booked_minutes()
        return used * 100 // (DAY_END - DAY_START)
