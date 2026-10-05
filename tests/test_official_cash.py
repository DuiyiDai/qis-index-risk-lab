"""Synthetic XML fixtures; tests never download market data."""
import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest

spec = importlib.util.spec_from_file_location(
    "cash_extract", Path(__file__).parents[1] / "scripts/prepare_official_cash.py")
cash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cash)


def xml(observations):
    body = ''.join(f'<Obs TIME_PERIOD="{d}" OBS_STATUS="{s}" OBS_VALUE="{v}"/>'
                   for d, s, v in observations)
    return f'<Root><Series SERIES_NAME="RIFSPFF_N.B">{body}</Series></Root>'.encode()


def test_conversion_and_missing_status_preserved():
    rows = cash.extract(xml([("2025-01-01", "ND", "-9999"),
                             ("2025-01-02", "A", "4.33")]), "2025-01-01", "2025-01-02")
    assert rows[0]["rate"] == ""
    assert rows[0]["source_percent"] == "-9999"
    assert float(rows[1]["rate"]) == pytest.approx(.0433)
    assert "available_date" not in rows[1]


@pytest.mark.parametrize("observations", [
    [("2025-01-02", "A", "nan")], [("2025-01-02", "A", "-9999")],
    [("2025-01-02", "UNKNOWN", "1")],
    [("2025-01-02", "A", "1"), ("2025-01-02", "A", "1")],
    [("2025-01-03", "A", "1"), ("2025-01-02", "A", "1")],
])
def test_bad_observations_fail(observations):
    with pytest.raises(ValueError):
        cash.extract(xml(observations), "2025-01-01", "2025-01-03")


def test_missing_series_fails():
    with pytest.raises(ValueError, match="exactly one"):
        cash.extract(b'<Root/>', "2025-01-01", "2025-01-03")


def test_replay_and_no_overwrite(tmp_path):
    archive, out = tmp_path / "input.zip", tmp_path / "out"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("H15_data.xml", xml([("2025-01-02", "A", "4.33")]))
    first = cash.prepare(archive, out, "2025-01-01", "2025-01-03")
    assert first == cash.prepare(archive, out, "2025-01-01", "2025-01-03")
    assert first["engine_ready"] is False
    original = (out / "observations.csv").read_bytes()
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("H15_data.xml", xml([("2025-01-02", "A", "4.34")]))
    with pytest.raises(ValueError, match="overwrite"):
        cash.prepare(archive, out, "2025-01-01", "2025-01-03")
    assert (out / "observations.csv").read_bytes() == original
