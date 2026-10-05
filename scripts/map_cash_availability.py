"""Offline, explicitly modeled H.15 release timing. No market-price fabrication."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

from qis_lab.data import Dataset, frame_bytes, rate_at

POLICY = "H15-CONSERVATIVE-CALENDAR-1"


def map_observations(observations, start, end):
    """Assume next joint federal/XNYS day 16:15, then first strictly later close.

    This intentionally delays use on stock-exchange-only holidays. The schedule
    is independent of future rate values and missing-observation patterns.
    It is a research assumption, not evidence of actual historical release times.
    """
    o = observations.copy()
    required = ["observation_date", "status", "source_percent", "rate"]
    if list(o.columns) != required or o.empty:
        raise ValueError("expected nonempty official observation contract")
    dates = pd.DatetimeIndex(pd.to_datetime(o.observation_date))
    if dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("invalid/duplicate/unordered observation dates")
    expected = pd.bdate_range(dates[0], dates[-1])
    if not dates.equals(expected):
        raise ValueError("missing or unexpected source weekday rows; preserve ND rows")
    if not o.status.isin(["A", "ND"]).all():
        raise ValueError("unreviewed observation status")
    active = o.status == "A"
    values = pd.to_numeric(o.loc[active, "rate"], errors="raise")
    percent = pd.to_numeric(o.loc[active, "source_percent"], errors="raise")
    if (not np.isfinite(values).all() or not values.between(0, 1).all()
            or not np.allclose(values, percent / 100, rtol=1e-14, atol=0)):
        raise ValueError("invalid or inconsistent rate units")
    if o.loc[~active, "rate"].notna().any():
        raise ValueError("ND observations must remain missing, never filled")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end or end > dates[-1]:
        raise ValueError("invalid requested coverage")
    cal = xcals.get_calendar("XNYS", start=dates[0] - pd.Timedelta(days=10),
                             end=max(end, dates[-1]) + pd.Timedelta(days=40))
    schedule = cal.schedule
    labels = schedule.index.tz_localize(None)
    holidays = USFederalHolidayCalendar().holidays(labels[0], labels[-1])
    joint_days = labels[~labels.isin(holidays)]
    closes = pd.DatetimeIndex(schedule["close"])
    rows = []
    for j in np.flatnonzero(active.to_numpy()):
        observed = dates[j]
        release_day = joint_days[joint_days.searchsorted(observed, side="right")]
        release = (release_day + pd.Timedelta(hours=16, minutes=15)).tz_localize(
            "America/New_York").tz_convert("UTC")
        position = closes.searchsorted(release, side="right")
        available = labels[position]
        rows.append({"observation_date": observed, "rate": float(o.iloc[j].rate),
                     "assumed_release_utc": release.isoformat(),
                     "available_date": available})
    audit = pd.DataFrame(rows)
    # Explicit consolidation: latest observation wins when multiple releases
    # first become usable at the same valuation close; audit retains all rows.
    audit["selected_at_close"] = ~audit.available_date.duplicated(keep="last")
    chosen = audit.loc[audit.selected_at_close].set_index("available_date")
    rates = chosen.loc[:end, ["observation_date", "rate"]].copy()
    valuation_dates = labels[(labels >= start) & (labels <= end)]
    if len(valuation_dates) < 2:
        raise ValueError("at least two valuation sessions required")
    data = Dataset(pd.DataFrame(), rates, {})  # Rate validation only; no fake asset inputs.
    check = []
    for day in valuation_dates:
        rate = rate_at(data, day)  # Uses the same bounded carry rule as the core.
        selected = rates.loc[:day].iloc[-1]
        check.append({"date": day, "observation_date": selected.observation_date,
                      "rate": rate, "age_days": (day - selected.observation_date).days})
    return rates, audit, pd.DataFrame(check).set_index("date")


def build(source: Path, out: Path, start: str, end: str):
    raw = (source / "observations.csv").read_bytes()
    parent = json.loads((source / "manifest.json").read_text())
    if sha256(raw).hexdigest() != parent["observations_sha256"]:
        raise ValueError("observation snapshot hash mismatch")
    if parent.get("series") != "RIFSPFF_N.B" or parent.get("mode") != "historical":
        raise ValueError("requires the official business-daily EFFR extraction")
    o = pd.read_csv(source / "observations.csv", float_precision="round_trip")
    rates, audit, checks = map_observations(o, start, end)
    artifacts = {"rates.csv": frame_bytes(rates),
                 "availability_audit.csv": audit.to_csv(index=False).encode(),
                 "daily_rate_check.csv": frame_bytes(checks)}
    manifest = {
        "policy": POLICY, "mode": "historical_rates_with_modeled_availability",
        "parent_manifest": parent, "evaluation_coverage": [start, end],
        "rates_rows": len(rates), "validated_closes": len(checks),
        "maximum_observation_age_days": int(checks.age_days.max()),
        "validation_status": "passed", "full_strategy_run": False,
        "availability_is_assumed": True, "point_in_time_verified": False,
        "policy_description": "Next day that is both XNYS-open and not a US federal "
            "holiday, 16:15 America/New_York; first XNYS close strictly afterwards. "
            "Latest observation wins explicit same-close consolidation.",
        "limitations": "Current revised snapshot; no historical release archive. "
            "Unscheduled Board closures/delayed releases not independently verified. "
            "Conservative on ordinary holidays but not a universal availability guarantee. "
            "EFFR is an interbank proxy, not an investable cash fund return.",
        "accrual": "At starting close choose latest eligible rate, age <=7 calendar days; "
            "cash interest = cash * decimal rate * actual calendar days / 360.",
        "dependencies": {"pandas": pd.__version__, "exchange_calendars": xcals.__version__},
        "code_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "output_sha256": {name: sha256(body).hexdigest() for name, body in artifacts.items()},
    }
    artifacts["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    out.mkdir(parents=True, exist_ok=True)
    for name, body in artifacts.items():
        path = out / name
        if path.exists() and path.read_bytes() != body:
            raise ValueError(f"refusing to overwrite different snapshot: {path}")
    for name, body in artifacts.items():
        (out / name).write_bytes(body)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--start", default="2004-11-18")
    parser.add_argument("--end", default="2025-12-31")
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.out, args.start, args.end), indent=2))
