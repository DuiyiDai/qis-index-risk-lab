from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from qis_lab.config import Config
from qis_lab.data import Dataset, hashes, synthetic, validate
from qis_lab.engine import run
from qis_lab.ledger import post_cost_wealth


def test_future_rates_do_not_change_past():
    d = synthetic("2023-01-03", "2025-03-31")
    revised = Dataset(d.prices.copy(), d.rates.copy(), d.metadata.copy())
    revised.rates.loc["2024-10-01":, "rate"] = 0.04
    a, _ = run(d, Config(strategy="cash"))
    b, _ = run(revised, Config(strategy="cash"))
    assert [r for r in a if r["date"] <= "2024-10-01"] == [
        r for r in b if r["date"] <= "2024-10-01"
    ]
    assert a[-1]["index"] != b[-1]["index"]


@pytest.mark.parametrize("target", [[-0.1, 0, 0], [1, 1, 0], [np.nan, 0, 0]])
def test_invalid_target(target):
    with pytest.raises(ValueError):
        post_cost_wealth(100, np.zeros(3), target, 0.0005)


def test_fully_invested_fee_solution():
    w = post_cost_wealth(100, np.zeros(3), np.ones(3) / 3, 0.0005)
    assert w == pytest.approx(100 / 1.0005)


def test_rate_duplicate_and_missing_dates():
    d = synthetic("2025-01-02", "2025-02-03")
    r = pd.concat([d.rates.iloc[:1], d.rates])
    with pytest.raises(ValueError, match="unique"):
        validate(Dataset(d.prices, r, d.metadata))
    r = d.rates.copy()
    r.iloc[0, 0] = pd.NaT
    with pytest.raises(ValueError, match="missing rate dates"):
        validate(Dataset(d.prices, r, d.metadata))


def test_historical_contract_inception_and_hash_gate():
    # Artificial schema fixture ONLY; never persisted or reported as market history.
    d = synthetic("2025-01-02", "2025-02-03")
    m = deepcopy(d.metadata)
    m.update(
        mode="historical",
        cash_kind="official_short_rate",
        rights_evidence="unit-test schema fixture, not permission",
    )
    m["permissions"] = {
        x: True for x in ["local_research", "automated_processing", "ai_assisted_processing"]
    }
    m["cash_source"] = {
        x: "schema fixture"
        for x in [
            "source_url",
            "retrieved_at",
            "source_basis",
            "accrual",
            "publication_lag",
            "availability",
            "permitted_uses",
        ]
    }
    m["instruments"] = {
        a: dict(
            instrument=a,
            currency="USD",
            return_type="total_return_reinvestment",
            source_url="schema fixture",
            retrieved_at="schema fixture",
            adjustment="fixture",
            inception="2026-01-01",
            permitted_uses="fixture",
            availability="fixture",
        )
        for a in d.prices.columns
    }
    candidate = Dataset(d.prices, d.rates, m)
    with pytest.raises(ValueError, match="pre-inception"):
        validate(candidate)
    for info in m["instruments"].values():
        info["inception"] = "2020-01-01"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate(candidate)
    m["snapshot_hashes"] = {k: v for k, v in hashes(candidate).items() if k != "metadata"}
    assert validate(candidate)["status"] == "passed"
    m["permissions"]["ai_assisted_processing"] = False
    with pytest.raises(ValueError, match="permission"):
        validate(candidate)
