"""Self-financing holdings ledger; prices represent reinvestment units."""

from dataclasses import dataclass, asdict
from datetime import date as calendar_date
import numpy as np
from .config import ASSETS


@dataclass
class State:
    date: str
    units: list
    cash: float
    wealth: float
    prices: list


def post_cost_wealth(prewealth, risky_values, target, cost):
    target = np.asarray(target, dtype=float)
    if not np.isfinite(target).all() or (target < 0).any() or target.sum() > 1 + 1e-12:
        raise ValueError("invalid unlevered target")
    if not 0 <= cost < 1 or prewealth <= 0:
        raise ValueError("invalid cost or wealth")
    # F(W)=W+c*sum|w_i W-v_i|-V is strictly increasing for c<1.
    lo, hi = 0.0, prewealth
    for _ in range(60):
        mid = (lo + hi) / 2
        if mid + cost * np.abs(target * mid - risky_values).sum() > prewealth:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2 if cost else prewealth


def step(state, date, prices, rate, instruction, cost_bps):
    prices = np.asarray(prices, dtype=float)
    units = np.asarray(state.units)
    days = (date - calendar_date.fromisoformat(state.date)).days
    pnl = units * (prices - np.array(state.prices))
    interest = state.cash * rate * days / 360
    pre_values = units * prices
    cash_pre = state.cash + interest
    prewealth = float(pre_values.sum() + cash_pre)
    trades = np.zeros(3)
    fee = 0.0
    wealth = prewealth
    if instruction is not None:
        target = np.array([instruction["target"][a] for a in ASSETS])
        wealth = post_cost_wealth(prewealth, pre_values, target, cost_bps / 10000)
        trades = target * wealth - pre_values
        fee = float(np.abs(trades).sum() * cost_bps / 10000)
        units = target * wealth / prices
        cash = float((1 - target.sum()) * wealth)
    else:
        cash = cash_pre
    error = float(wealth - state.wealth - pnl.sum() - interest + fee)
    if cash < -1e-10 or abs(error) > 1e-9:
        raise ArithmeticError("self-financing reconciliation failed")
    new = State(str(date), units.tolist(), cash, wealth, prices.tolist())
    row = {
        "date": str(date),
        "previous_wealth": state.wealth,
        "index": wealth,
        "pretrade_wealth": prewealth,
        "pretrade_units": state.units,
        "prices": prices.tolist(),
        "pretrade_cash": cash_pre,
        "units": units.tolist(),
        "cash": cash,
        "asset_pnl": pnl.tolist(),
        "cash_interest": interest,
        "cost": fee,
        "trades": trades.tolist(),
        "turnover": float(np.abs(trades).sum() / prewealth),
        "weights": (units * prices / wealth).tolist(),
        "cash_weight": cash / wealth,
        "cash_rate": rate,
        "calendar_days": days,
        "instruction": instruction,
        "reconciliation_error": error,
    }
    return new, row


def state_dict(state):
    return asdict(state)
