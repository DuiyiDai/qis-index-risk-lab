import math
import pytest
from qis_lab.pricing import option, delta_mapping


@pytest.mark.parametrize(
    "spot,strike,time,rate,vol",
    [(100, 100, 1, 0.03, 0.2), (80, 110, 0.5, -0.01, 0.4), (150, 90, 2, 0.05, 0.1)],
)
def test_parity_bounds_greeks(spot, strike, time, rate, vol):
    c = option(spot, strike, time, rate, vol)
    p = option(spot, strike, time, rate, vol, "put")
    assert c["price"] - p["price"] == pytest.approx(spot - strike * math.exp(-rate * time))
    assert max(0, spot - strike * math.exp(-rate * time)) <= c["price"] <= spot
    h = 0.01
    up = option(spot + h, strike, time, rate, vol)["price"]
    dn = option(spot - h, strike, time, rate, vol)["price"]
    assert (up - dn) / (2 * h) == pytest.approx(c["delta"], abs=1e-6)
    assert (up - 2 * c["price"] + dn) / h**2 == pytest.approx(c["gamma"], abs=1e-6)
    vup = option(spot, strike, time, rate, vol + 0.0001)["price"]
    vdn = option(spot, strike, time, rate, vol - 0.0001)["price"]
    assert (vup - vdn) / 0.0002 * 0.01 == pytest.approx(c["vega_per_1pct"], abs=1e-6)


def test_limits_units_and_signs():
    assert option(110, 100, 0, 0.03, 0.2)["price"] == 10
    assert option(100, 100, 0, 0.03, 0.2)["delta"] is None
    assert option(100, 100, 1, 0, 0)["gamma"] is None
    assert option(110, 100, 1, 0, 0)["price"] == 10
    c = option(100, 100, 1, 0.03, 0.2)
    short = option(100, 100, 1, 0.03, 0.2, units=-10)
    for key in c:
        assert short[key] == pytest.approx(-10 * c[key])
    m = delta_mapping(c["delta"], 100, [0.3, 0.2, 0.1])
    assert all(x > 0 for x in m["replication_risky_dollars"])
    assert all(x < 0 for x in m["offset_hedge_risky_dollars"])
    p = option(100, 100, 1, 0.03, 0.2, "put")
    assert delta_mapping(p["delta"], 100, [0.3, 0.2, 0.1])["offset_hedge_risky_dollars"][0] > 0


@pytest.mark.parametrize(
    "args",
    [
        (0, 100, 1, 0, 0.2),
        (100, 100, -1, 0, 0.2),
        (100, 100, 1, 0, -0.1),
        (float("nan"), 100, 1, 0, 0.2),
    ],
)
def test_invalid(args):
    with pytest.raises(ValueError):
        option(*args)
