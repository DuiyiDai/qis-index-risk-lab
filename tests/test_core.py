from dataclasses import replace
import json
import numpy as np
import pandas as pd
import pytest
from qis_lab.config import ASSETS, Config
from qis_lab.data import Dataset, synthetic, validate, rate_at, month_ends, write_csv, load_csv
from qis_lab.engine import run
from qis_lab.signals import decisions
from qis_lab.ledger import State, step
from qis_lab.reference import reference_ledger


@pytest.fixture(scope="module")
def data():
    return synthetic("2023-01-03", "2025-03-31")


def test_miniature_independent_reference():
    p = pd.read_csv("fixtures/miniature.csv")
    dates = p.date.tolist()
    prices = p[list(ASSETS)].values.tolist()
    targets = [None, [0.5, 0, 0], None, [0, 0, 0]]
    state = State(dates[0], [0, 0, 0], 100, 100, prices[0])
    rows = []
    for j in range(1, len(dates)):
        instruction = {"target": dict(zip(ASSETS, targets[j]))} if targets[j] is not None else None
        state, row = step(state, pd.Timestamp(dates[j]).date(), prices[j], 0, instruction, 5)
        rows.append(row)
    w = 100 / 1.00025
    expected = [w, 1.05 * w, (1.05 - 0.000275) * w]
    np.testing.assert_allclose([r["index"] for r in rows], expected, atol=1e-10, rtol=0)
    np.testing.assert_allclose(
        reference_ledger(dates, prices, targets, [0] * 4, 5), expected, atol=1e-10, rtol=0
    )
    assert rows[0]["cost"] > 0 and rows[2]["cost"] > 0
    assert rows[1]["weights"][0] == pytest.approx(0.55 / 1.05)


def test_future_perturbation(data):
    cutoff = "2024-07-01"
    altered = Dataset(data.prices.copy(), data.rates.copy(), data.metadata.copy())
    altered.prices.loc[altered.prices.index > cutoff] *= [1.5, 0.7, 2]
    a, _ = run(data)
    b, _ = run(altered)
    assert [r for r in a if r["date"] <= cutoff] == [r for r in b if r["date"] <= cutoff]
    da, db = decisions(data.prices), decisions(altered.prices)
    assert {d: v for d, v in da.items() if d <= cutoff} == {
        d: v for d, v in db.items() if d <= cutoff
    }


def test_execution_lag(data):
    d = decisions(data.prices)
    assert d["2025-01-31"]["execution_date"] == "2025-02-03"
    rows, _ = run(data)
    bydate = {r["date"]: r for r in rows}
    row = bydate["2025-02-03"]
    assert row["instruction"]["decision_date"] == "2025-01-31"
    prev = bydate["2025-01-31"]
    np.testing.assert_allclose(
        row["asset_pnl"], np.array(prev["units"]) * (np.array(row["prices"]) - prev["prices"])
    )
    nxt = bydate["2025-02-04"]
    np.testing.assert_allclose(
        nxt["asset_pnl"], np.array(row["units"]) * (np.array(nxt["prices"]) - row["prices"])
    )


def test_reconciliation_and_reference(data):
    rows, _ = run(data)
    anchor = data.prices.index.get_loc(pd.Timestamp(rows[0]["date"])) - 1
    dates = [str(data.prices.index[anchor].date())] + [r["date"] for r in rows]
    prices = [data.prices.iloc[anchor].tolist()] + [r["prices"] for r in rows]
    targets = [None] + [
        list(r["instruction"]["target"].values()) if r["instruction"] else None for r in rows
    ]
    rates = [r["cash_rate"] for r in rows] + [0]
    ref = reference_ledger(dates, prices, targets, rates, 5)
    np.testing.assert_allclose(ref, [r["index"] for r in rows], atol=1e-9, rtol=0)
    for r in rows:
        assert r["cash"] >= -1e-12
        assert sum(r["weights"]) + r["cash_weight"] == pytest.approx(1)
        assert r["index"] - r["previous_wealth"] == pytest.approx(
            sum(r["asset_pnl"]) + r["cash_interest"] - r["cost"], abs=1e-10
        )
        assert r["pretrade_wealth"] == pytest.approx(r["index"] + r["cost"])


def test_incremental_json_replay(data):
    batch, _ = run(data)
    a, saved = run(data, stop="2024-10-31")
    b, _ = run(data, saved=json.loads(json.dumps(saved)))
    assert batch == a + b
    revised = Dataset(data.prices.copy(), data.rates.copy(), data.metadata.copy())
    revised.prices.iloc[300, 0] *= 1.01
    with pytest.raises(ValueError, match="prefix changed"):
        run(revised, saved=saved)


def test_deterministic_and_zero_cost(data):
    a, _ = run(data, Config(cost_bps=0))
    b, _ = run(data, Config(cost_bps=0))
    assert a == b
    assert all(r["cost"] == 0 for r in a)
    for r in a[1:]:
        value = sum(q * p for q, p in zip(r["pretrade_units"], r["prices"])) + r["pretrade_cash"]
        assert r["index"] == pytest.approx(value)


def test_all_cash_and_weekend(data):
    rows, _ = run(data, Config(strategy="cash"))
    assert all(sum(r["weights"]) == 0 and r["cost"] == 0 for r in rows)
    r = next(r for r in rows[1:] if r["calendar_days"] == 3)
    assert r["index"] == pytest.approx(r["previous_wealth"] * (1 + 0.02 * 3 / 360))


def test_zero_vol_and_insufficient(data):
    p = data.prices.copy()
    p[:] = 100
    d = decisions(p)
    assert all(x["sigma_base"] == 0 and sum(x["target"].values()) == 0 for x in d.values())
    p[:] = np.arange(len(p))[:, None] * 0.01 + 100
    d = decisions(p)
    assert all(x["scale"] <= 1 for x in d.values())
    short = synthetic("2025-01-02", "2025-02-03")
    with pytest.raises(ValueError, match="warm-up"):
        run(short)


@pytest.mark.parametrize("problem", ["missing", "duplicate", "nan", "zero", "unordered"])
def test_bad_prices(data, problem):
    p = data.prices.copy()
    if problem == "missing":
        p = p.drop(p.index[10])
    if problem == "duplicate":
        p = pd.concat([p.iloc[:1], p])
    if problem == "nan":
        p.iloc[10, 0] = np.nan
    if problem == "zero":
        p.iloc[10, 0] = 0
    if problem == "unordered":
        p = p.iloc[::-1]
    with pytest.raises(ValueError):
        validate(Dataset(p, data.rates, data.metadata))


def test_rate_availability_and_bound(data):
    r = data.rates.iloc[:1].copy()
    d = Dataset(data.prices, r, data.metadata)
    assert rate_at(d, r.index[0] + pd.Timedelta(days=7)) == 0.02
    with pytest.raises(ValueError, match="stale"):
        rate_at(d, r.index[0] + pd.Timedelta(days=8))
    with pytest.raises(ValueError, match="no cash rate"):
        rate_at(d, r.index[0] - pd.Timedelta(days=1))
    future = data.rates.copy()
    future.iloc[0, 0] = future.index[0] + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="before observation"):
        validate(Dataset(data.prices, future, data.metadata))


def test_truncated_calendar(data):
    p = data.prices.loc[:"2025-03-14"]
    assert pd.Timestamp("2025-03-14") not in month_ends(p.index)
    assert pd.Timestamp("2025-03-31") in month_ends(p.index)


def test_csv_roundtrip(data, tmp_path):
    write_csv(data, tmp_path)
    loaded = load_csv(tmp_path)
    assert run(data)[0] == run(loaded)[0]


def test_historical_gate(data):
    m = dict(data.metadata, mode="historical")
    with pytest.raises(ValueError, match="official short-rate"):
        validate(Dataset(data.prices, data.rates, m))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cost_bps": -1},
        {"cost_bps": float("nan")},
        {"vol_window": 1},
        {"vol_reference": 0},
        {"strategy": "short"},
    ],
)
def test_bad_config(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_benchmark_monthly_and_drift(data):
    rows, _ = run(data, replace(Config(), strategy="equal"))
    assert sum(r["instruction"] is not None for r in rows) < len(rows) / 10
    assert any(abs(r["weights"][0] - 1 / 3) > 1e-5 for r in rows if r["instruction"] is None)
