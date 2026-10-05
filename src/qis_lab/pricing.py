"""Hypothetical non-distributing lognormal surrogate; not strategy valuation."""

from math import erf, exp, isfinite, log, pi, sqrt


def option(spot, strike, maturity, rate, volatility, kind="call", units=1.0):
    if not all(isfinite(x) for x in (spot, strike, maturity, rate, volatility, units)):
        raise ValueError("finite inputs required")
    if spot <= 0 or strike <= 0 or maturity < 0 or volatility < 0 or kind not in {"call", "put"}:
        raise ValueError("positive spot/strike, nonnegative time/volatility, call or put required")
    sign = 1 if kind == "call" else -1
    discounted = strike * exp(-rate * maturity)
    if maturity == 0 or volatility == 0:
        difference = spot - (strike if maturity == 0 else discounted)
        delta = sign * (1.0 if sign * difference > 0 else 0.0) if difference else None
        return {
            "price": units * max(sign * difference, 0.0),
            "delta": None if delta is None else units * delta,
            "gamma": None if difference == 0 else 0.0,
            "vega_per_1pct": None if difference == 0 else 0.0,
        }

    def normal(x):
        return 0.5 * (1 + erf(x / sqrt(2)))

    d1 = (log(spot / strike) + (rate + 0.5 * volatility**2) * maturity) / (
        volatility * sqrt(maturity)
    )
    d2 = d1 - volatility * sqrt(maturity)
    density = exp(-0.5 * d1 * d1) / sqrt(2 * pi)
    return {
        "price": units * sign * (spot * normal(sign * d1) - discounted * normal(sign * d2)),
        "delta": units * sign * normal(sign * d1),
        "gamma": units * density / (spot * volatility * sqrt(maturity)),
        "vega_per_1pct": units * spot * density * sqrt(maturity) * 0.01,
    }


def delta_mapping(delta, spot, weights):
    if delta is None:
        raise ValueError("delta undefined at kink")
    if (
        len(weights) != 3
        or not all(isfinite(w) and w >= 0 for w in weights)
        or sum(weights) > 1 + 1e-12
    ):
        raise ValueError("valid frozen weights required")
    exposure = [delta * spot * w for w in weights]
    return {
        "replication_risky_dollars": exposure,
        "offset_hedge_risky_dollars": [-x for x in exposure],
        "replication_cash_dollars": delta * spot * (1 - sum(weights)),
    }
