"""Frozen local CSV contract and strict calendar/availability validation."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import exchange_calendars as xcals
import numpy as np
import pandas as pd
from .config import ASSETS


@dataclass
class Dataset:
    prices: pd.DataFrame
    rates: pd.DataFrame
    metadata: dict


def sessions(start, end):
    return xcals.get_calendar("XNYS", start=start, end=end).sessions.tz_localize(None)


def month_ends(index):
    # Extend through the complete last calendar month, never infer from a truncated file.
    full = sessions(index[0].replace(day=1), index[-1] + pd.offsets.MonthEnd(0))
    ends = full.to_series().groupby(full.to_period("M")).last()
    return set(ends)


def frame_bytes(frame):
    return frame.to_csv(index=True, float_format="%.17g", date_format="%Y-%m-%d").encode()


def hashes(data):
    return {
        "prices": sha256(frame_bytes(data.prices)).hexdigest(),
        "rates": sha256(frame_bytes(data.rates)).hexdigest(),
        "metadata": sha256(json.dumps(data.metadata, sort_keys=True).encode()).hexdigest(),
    }


def validate(data):
    p, r, m = data.prices, data.rates, data.metadata
    if list(p.columns) != list(ASSETS) or len(p) < 2:
        raise ValueError("prices require date,equity,treasury,gold and >=2 rows")
    if p.index.has_duplicates or not p.index.is_monotonic_increasing:
        raise ValueError("duplicate or unordered price sessions")
    expected = sessions(m["coverage_start"], m["coverage_end"])
    if not p.index.equals(expected):
        raise ValueError(
            f"session mismatch: missing={expected.difference(p.index).tolist()[:5]}, "
            f"unexpected={p.index.difference(expected).tolist()[:5]}"
        )
    if not np.isfinite(p.to_numpy()).all() or (p <= 0).any().any():
        raise ValueError("positive finite complete prices required; no fills")
    if (
        list(r.columns) != ["observation_date", "rate"]
        or r.index.has_duplicates
        or not r.index.is_monotonic_increasing
    ):
        raise ValueError("rates need ordered unique available_date,observation_date,rate")
    if not np.isfinite(r.rate).all() or (r.rate < 0).any() or (r.rate > 1).any():
        raise ValueError("rates must be decimal annual values between 0 and 1")
    if r.index.hasnans or pd.DatetimeIndex(r.observation_date).hasnans:
        raise ValueError("missing rate dates")
    if (pd.DatetimeIndex(r.observation_date) > r.index).any():
        raise ValueError("rate available before observation")
    if m["mode"] not in {"synthetic", "historical"}:
        raise ValueError("explicit mode required")
    if m["mode"] == "historical":
        if m.get("cash_kind") != "official_short_rate":
            raise ValueError("historical requires official short-rate inputs, not assumed rates")
        for permission in ("local_research", "automated_processing", "ai_assisted_processing"):
            if m.get("permissions", {}).get(permission) is not True:
                raise ValueError(f"missing documented permission: {permission}")
        if not m.get("rights_evidence") or "REQUIRED" in m["rights_evidence"]:
            raise ValueError("documented rights evidence required")
        for key in (
            "source_url",
            "retrieved_at",
            "source_basis",
            "accrual",
            "publication_lag",
            "availability",
            "permitted_uses",
        ):
            value = m.get("cash_source", {}).get(key)
            if not value or "REQUIRED" in str(value):
                raise ValueError(f"cash source metadata required: {key}")
        if set(m.get("instruments", {})) != set(ASSETS):
            raise ValueError("instrument metadata required for each sleeve")
        for a in ASSETS:
            info = m["instruments"][a]
            for key in (
                "instrument",
                "currency",
                "return_type",
                "source_url",
                "retrieved_at",
                "adjustment",
                "inception",
                "permitted_uses",
                "availability",
            ):
                if not info.get(key) or "REQUIRED" in str(info[key]):
                    raise ValueError(f"missing instrument metadata {a}.{key}")
            if info["currency"] != "USD" or info["return_type"] != "total_return_reinvestment":
                raise ValueError("USD total-return reinvestment prices required")
            if p.index[0] < pd.Timestamp(info["inception"]):
                raise ValueError(f"pre-inception history: {a}")
        if (
            m.get("snapshot_hashes", {}).get("prices") != hashes(data)["prices"]
            or m.get("snapshot_hashes", {}).get("rates") != hashes(data)["rates"]
        ):
            raise ValueError("snapshot hash mismatch")
    # Check every interval even if the strategy would happen to have zero cash.
    for date in p.index[:-1]:
        rate_at(data, date)
    return {"status": "passed", "sessions": len(p), "calendar": "XNYS"}


def rate_at(data, date):
    eligible = data.rates.loc[:date]
    if eligible.empty:
        raise ValueError(f"no cash rate available at starting close {date.date()}")
    row = eligible.iloc[-1]
    if (date - pd.Timestamp(row.observation_date)).days > 7:
        raise ValueError(f"cash rate stale beyond seven calendar days at {date.date()}")
    return float(row.rate)


def load_csv(folder):
    root = Path(folder)
    p = pd.read_csv(
        root / "prices.csv", index_col="date", parse_dates=["date"], float_precision="round_trip"
    )
    r = pd.read_csv(
        root / "rates.csv",
        index_col="available_date",
        parse_dates=["available_date", "observation_date"],
        float_precision="round_trip",
    )
    data = Dataset(p, r, json.loads((root / "metadata.json").read_text()))
    validate(data)
    return data


def write_csv(data, folder):
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=True)
    (root / "prices.csv").write_bytes(frame_bytes(data.prices))
    (root / "rates.csv").write_bytes(frame_bytes(data.rates))
    (root / "metadata.json").write_text(json.dumps(data.metadata, indent=2, sort_keys=True))


def synthetic(start="2004-01-02", end="2025-12-31", seed=1729):
    dates = sessions(start, end)
    rng = np.random.default_rng(seed)
    returns = np.zeros((len(dates), 3))
    # Repeating designed regimes: rising, falling, exactly flat, volatility shock.
    for j in range(1, len(dates)):
        regime = (j // 315) % 4
        if regime == 2:
            continue
        mu = [0.0007, -0.0008, 0, -0.0002][regime]
        vol = [0.006, 0.009, 0, 0.035][regime]
        common = rng.normal()
        returns[j] = mu + vol * np.array([1, 0.4, 0.8]) * (
            0.35 * common + 0.93675 * rng.normal(size=3)
        )
    p = pd.DataFrame(100 * np.cumprod(1 + returns, axis=0), index=dates.copy(), columns=ASSETS)
    p.index.name = "date"
    r = pd.DataFrame({"observation_date": dates, "rate": 0.02}, index=dates.copy())
    r.index.name = "available_date"
    return Dataset(
        p,
        r,
        {
            "mode": "synthetic",
            "seed": seed,
            "cash_kind": "assumed_2pct_ACT360",
            "coverage_start": str(dates[0].date()),
            "coverage_end": str(dates[-1].date()),
            "source_url": "generated:src/qis_lab/data.py",
            "availability": "known deterministic demo rate at starting close",
            "currency": "USD",
            "return_type": "synthetic_reinvestment",
            "permitted_uses": "project-generated synthetic fixtures; public demo",
            "retrieved_at": "not applicable; generated deterministically",
        },
    )
