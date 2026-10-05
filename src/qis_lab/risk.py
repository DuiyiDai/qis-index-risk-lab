"""Metrics use actual wealth returns and the same calendar cash accrual."""

import numpy as np
import pandas as pd


def metrics(rows):
    if not rows:
        return {}
    levels = np.array([r["index"] for r in rows])
    previous = np.array([r["previous_wealth"] for r in rows])
    ret = levels / previous - 1
    cashret = np.array([r["cash_rate"] * r["calendar_days"] / 360 for r in rows])
    excess = ret - cashret
    days = sum(r["calendar_days"] for r in rows)
    vol = float(np.std(ret, ddof=1) * np.sqrt(252)) if len(ret) > 1 else None
    ex_sd = np.std(excess, ddof=1) if len(excess) > 1 else 0
    running_peak = np.maximum.accumulate(np.r_[previous[0], levels])[1:]
    return {
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "sessions": len(rows),
        "annual_return": float((levels[-1] / previous[0]) ** (365.25 / days) - 1) if days else None,
        "annual_vol": vol,
        "sharpe": float(np.mean(excess) / ex_sd * np.sqrt(252)) if ex_sd > 1e-12 else None,
        "max_drawdown": float(np.min(levels / running_peak - 1)),
        "turnover_total": sum(r["turnover"] for r in rows),
        "cost_index_points": sum(r["cost"] for r in rows),
        "final_index": float(levels[-1]),
        "mean_risky_exposure": float(np.mean([sum(r["weights"]) for r in rows])),
    }


def risk_series(rows, window=63):
    ret = pd.Series([r["index"] / r["previous_wealth"] - 1 for r in rows])
    trailing = ret.rolling(window).std(ddof=1) * np.sqrt(252)
    # At execution t, subsequently realized observations t+1 ... t+window.
    forward = ret.shift(-1).iloc[::-1].rolling(window).std(ddof=1).iloc[::-1] * np.sqrt(252)
    return [
        {
            "date": row["date"],
            "forecast_target_vol": row["instruction"]["forecast_target_vol"]
            if row["instruction"]
            else None,
            "trailing_realized_vol": None if pd.isna(trailing[j]) else float(trailing[j]),
            "subsequent_realized_vol": None if pd.isna(forward[j]) else float(forward[j]),
        }
        for j, row in enumerate(rows)
    ]


def frozen_shocks(row, amount=1_000_000):
    scenarios = {
        "equity -20%": [-0.20, 0, 0],
        "Treasuries -10%": [0, -0.10, 0],
        "gold -15%": [0, 0, -0.15],
        "joint selloff": [-0.20, -0.10, -0.15],
    }
    return {
        "label": "Hypothetical instantaneous frozen-holdings shocks; no advance rebalance",
        "investment_usd": amount,
        "risky_notionals_usd": [amount * w for w in row["weights"]],
        "cash_usd": amount * row["cash_weight"],
        "shocks": {
            name: {
                "return": float(np.dot(row["weights"], shock)),
                "pnl_usd": float(amount * np.dot(row["weights"], shock)),
            }
            for name, shock in scenarios.items()
        },
    }
