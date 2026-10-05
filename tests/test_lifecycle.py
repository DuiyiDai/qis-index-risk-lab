import json
import pytest
from qis_lab.data import synthetic, Dataset
from qis_lab.engine import run
from qis_lab.reporting import persist


def test_revision_immutable_idempotent(tmp_path):
    data = synthetic("2023-01-03", "2025-03-31")
    rows, state = run(data)
    old = persist(data, rows, state, tmp_path)
    content = (old / "ledger.json").read_bytes()
    assert persist(data, rows, state, tmp_path) == old
    revised = Dataset(data.prices.copy(), data.rates.copy(), dict(data.metadata, revision="v2"))
    revised.prices.loc["2024-07-01", "equity"] *= 1.02
    changed, saved = run(revised)
    new = persist(revised, changed, saved, tmp_path)
    assert new != old and (old / "ledger.json").read_bytes() == content
    assert [r for r in rows if r["date"] < "2024-07-01"] == [
        r for r in changed if r["date"] < "2024-07-01"
    ]
    assert any(a != b for a, b in zip(rows, changed))
    assert len(list(tmp_path.iterdir())) == 2
    assert json.loads((new / "manifest.json").read_text())["validation"]["status"] == "passed"
    with pytest.raises(ValueError, match="collision"):
        persist(data, changed, state, tmp_path)
