import numpy as np
import pytest
from qis_lab.risk import metrics, risk_series, frozen_shocks
from qis_lab.data import synthetic
from qis_lab.engine import run
from qis_lab.signals import decisions
from qis_lab.config import Config


def test_covariance_and_monthly_signal_formula():
    d = synthetic("2023-01-03", "2025-03-31")
    decision = decisions(d.prices)["2025-01-31"]
    p = d.prices
    j = p.index.get_loc("2025-01-31")
    signal = (p.iloc[j] / p.iloc[j - 252] - 1 > 0).to_numpy(dtype=float)
    r = p.iloc[j - 63 : j + 1].to_numpy()
    returns = r[1:] / r[:-1] - 1
    centered = returns - returns.mean(axis=0)
    cov = centered.T @ centered / 62
    b = signal / 3
    sigma = np.sqrt(252 * b @ cov @ b)
    np.testing.assert_array_equal(decision["signals"], signal)
    assert decision["sigma_base"] == pytest.approx(sigma)
    assert decision["scale"] == pytest.approx(min(1, 0.1 / max(sigma, 0.01)))


def test_realized_window_alignment_and_cash_sharpe():
    d = synthetic("2023-01-03", "2025-03-31")
    rows, _ = run(d)
    series = risk_series(rows)
    future = [r["index"] / r["previous_wealth"] - 1 for r in rows[1:64]]
    assert series[0]["subsequent_realized_vol"] == pytest.approx(
        np.std(future, ddof=1) * np.sqrt(252)
    )
    assert series[-1]["subsequent_realized_vol"] is None
    assert series[0]["trailing_realized_vol"] is None
    cash, _ = run(d, Config(strategy="cash"))
    assert metrics(cash)["sharpe"] is None
    shock = frozen_shocks(rows[-1])
    assert shock["shocks"]["equity -20%"]["return"] == pytest.approx(-0.2 * rows[-1]["weights"][0])
