"""Category weights and the weighted average of category percentages."""


def check_weights(weights):
    total = sum(weights.values())
    if total != 100:
        raise ValueError("weights must sum to 100")
    return weights


def active_weight(weights, percents):
    total = 0
    for category in percents:
        total += weights[category]
    return total


def weighted_average(weights, percents):
    total = active_weight(weights, percents)
    if total == 0:
        return 0
    points = 0
    for category in percents:
        points += weights[category] * percents[category]
    return (points * 2 + total) // (total * 2)
