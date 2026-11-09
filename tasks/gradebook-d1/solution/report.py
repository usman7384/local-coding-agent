"""Gradebook: collect scores per student and report final grades."""

from scores import average, drop_lowest, late_penalty, percentage
from weights import check_weights, weighted_average

CUTOFFS = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


class Gradebook:
    def __init__(self, weights, drops=None):
        self.weights = check_weights(weights)
        self.drops = drops or {}
        self.scores = {}

    def add_score(self, student, category, points, possible, days_late=0):
        percent = late_penalty(percentage(points, possible), days_late)
        grades = self.scores.setdefault(student, {})
        grades.setdefault(category, []).append(percent)

    def category_percent(self, student, category):
        values = self.scores.get(student, {}).get(category, [])
        if not values:
            return None
        kept = drop_lowest(values, self.drops.get(category, 0))
        return average(kept)

    def final(self, student):
        percents = {}
        for category in self.weights:
            value = self.category_percent(student, category)
            if value is not None:
                percents[category] = value
        return weighted_average(self.weights, percents)

    def letter(self, student):
        value = self.final(student)
        for cutoff, grade in CUTOFFS:
            if value >= cutoff:
                return grade
        return "F"

    def ranking(self):
        order = sorted(self.scores, key=lambda s: (-self.final(s), s))
        result = []
        rank = 0
        for index, student in enumerate(order):
            if index == 0 or self.final(student) != self.final(order[index - 1]):
                rank = index + 1
            result.append((student, rank))
        return result
