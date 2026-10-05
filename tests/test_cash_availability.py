"""Calendar timing tests use synthetic rate values; offline only."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from qis_lab.data import Dataset, rate_at
from qis_lab.ledger import State, step

spec = importlib.util.spec_from_file_location(
    "cash_map", Path(__file__).parents[1] / "scripts/map_cash_availability.py")
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)


def observations(start="2024-12-16", end="2025-01-24"):
    dates = pd.bdate_range(start, end)
    return pd.DataFrame({"observation_date": dates, "status": "A",
                         "source_percent": 3.6, "rate": .036})


def mapping(frame=None, start="2025-01-02", end="2025-01-24"):
    return mapper.map_observations(observations() if frame is None else frame, start, end)


def test_after_close_lag_and_funeral_closure():
    rates, audit, checks = mapping()
    indexed = audit.set_index("observation_date")
    # Thursday observation, Friday after-close assumed publication, Monday use.
    assert indexed.loc["2025-01-02", "available_date"] == pd.Timestamp("2025-01-06")
    # Jan 9 XNYS funeral closure deliberately delays Jan 8 observation further.
    assert indexed.loc["2025-01-08", "available_date"] == pd.Timestamp("2025-01-13")
    assert pd.Timestamp("2025-01-09") not in checks.index
    assert rates.index.is_unique
    assert (audit.available_date > audit.observation_date).all()
    assert not indexed.loc["2025-01-08", "selected_at_close"]
    assert indexed.loc["2025-01-09", "selected_at_close"]


def test_federal_holiday_when_exchange_open():
    frame = observations("2024-09-23", "2024-10-18")
    _, audit, _ = mapping(frame, "2024-10-01", "2024-10-18")
    row = audit.set_index("observation_date").loc["2024-10-11"]
    assert row.available_date == pd.Timestamp("2024-10-16")  # Oct 14 federal holiday


def test_dst_changes_utc_not_local_release_hour():
    frame = observations("2025-02-24", "2025-03-14")
    _, audit, _ = mapping(frame, "2025-03-03", "2025-03-14")
    rows = audit.set_index("observation_date")
    assert "21:15:00+00:00" in rows.loc["2025-03-06", "assumed_release_utc"]
    assert "20:15:00+00:00" in rows.loc["2025-03-07", "assumed_release_utc"]


def test_future_changes_cannot_change_past_available_rates():
    frame = observations()
    old_rates, _, old_checks = mapping(frame)
    frame.loc[frame.observation_date >= "2025-01-13", ["rate", "source_percent"]] = [.09, 9]
    new_rates, _, new_checks = mapping(frame)
    pd.testing.assert_frame_equal(old_rates.loc[:"2025-01-13"], new_rates.loc[:"2025-01-13"])
    pd.testing.assert_frame_equal(old_checks.loc[:"2025-01-13"], new_checks.loc[:"2025-01-13"])


def test_cash_interest_uses_start_close_and_calendar_days():
    rates, _, _ = mapping()
    data = Dataset(pd.DataFrame(), rates, {})
    state = State("2025-01-17", [0, 0, 0], 100, 100, [1, 1, 1])
    updated, row = step(state, pd.Timestamp("2025-01-21").date(), [1, 1, 1],
                        rate_at(data, pd.Timestamp(state.date)), None, 5)
    assert row["calendar_days"] == 4
    assert row["cash_interest"] == pytest.approx(.04)
    assert updated.cash == pytest.approx(100.04)
    assert row["cost"] == 0


def test_missing_weekday_and_filled_nd_fail():
    with pytest.raises(ValueError, match="weekday"):
        mapping(observations().drop(index=5))
    frame = observations()
    frame.loc[5, "status"] = "ND"
    with pytest.raises(ValueError, match="never filled"):
        mapping(frame)


def test_long_missing_run_fails_staleness_not_backfilled():
    frame = observations()
    missing = frame.observation_date >= "2025-01-01"
    frame.loc[missing, "status"] = "ND"
    frame.loc[missing, "rate"] = float("nan")
    frame.loc[missing, "source_percent"] = -9999
    with pytest.raises(ValueError, match="stale"):
        mapping(frame)


def test_deterministic_and_insufficient_prior_history():
    a, b, c = mapping()
    x, y, z = mapping()
    for left, right in [(a, x), (b, y), (c, z)]:
        pd.testing.assert_frame_equal(left, right)
    with pytest.raises(ValueError, match="no cash rate"):
        mapping(observations("2025-01-02", "2025-01-24"))


def test_files_hashes_replay_and_collision(tmp_path):
    import json
    from hashlib import sha256

    source, out = tmp_path / "source", tmp_path / "out"
    source.mkdir()
    raw = observations().to_csv(index=False).encode()
    (source / "observations.csv").write_bytes(raw)
    parent = {"observations_sha256": sha256(raw).hexdigest(),
              "series": "RIFSPFF_N.B", "mode": "historical"}
    (source / "manifest.json").write_text(json.dumps(parent))
    first = mapper.build(source, out, "2025-01-02", "2025-01-24")
    assert first == mapper.build(source, out, "2025-01-02", "2025-01-24")
    rates = pd.read_csv(out / "rates.csv", parse_dates=["available_date", "observation_date"],
                        index_col="available_date", float_precision="round_trip")
    assert rate_at(Dataset(pd.DataFrame(), rates, {}), pd.Timestamp("2025-01-17")) == .036
    for name, expected in first["output_sha256"].items():
        assert sha256((out / name).read_bytes()).hexdigest() == expected
    with pytest.raises(ValueError, match="overwrite"):
        mapper.build(source, out, "2025-01-03", "2025-01-24")
    (source / "observations.csv").write_bytes(raw + b'\n')
    with pytest.raises(ValueError, match="hash mismatch"):
        mapper.build(source, tmp_path / "new", "2025-01-02", "2025-01-24")
