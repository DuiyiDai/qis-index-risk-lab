"""Independent scalar reference: fixed-point fees, ordinary Python lists.
No imports from the main ledger. Target instructions are test inputs.
"""

from datetime import date


def reference_ledger(dates, prices, targets, rates, cost_bps):
    q, cash, wealth = [0.0, 0.0, 0.0], 100.0, 100.0
    result = []
    for j in range(1, len(dates)):
        days = (date.fromisoformat(dates[j]) - date.fromisoformat(dates[j - 1])).days
        cash *= 1 + rates[j - 1] * days / 360
        values = [q[k] * prices[j][k] for k in range(3)]
        before = cash + sum(values)
        weights = targets[j]
        if weights is not None:
            wealth = before
            for _ in range(100):
                fees = (
                    cost_bps / 10000 * sum(abs(weights[k] * wealth - values[k]) for k in range(3))
                )
                updated = before - fees
                if abs(updated - wealth) < 1e-13:
                    wealth = updated
                    break
                wealth = updated
            q = [weights[k] * wealth / prices[j][k] for k in range(3)]
            cash = wealth * (1 - sum(weights))
        else:
            wealth = before
        result.append(wealth)
    return result
