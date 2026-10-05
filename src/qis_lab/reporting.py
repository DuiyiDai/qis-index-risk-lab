"""Immutable content-addressed runs. Synthetic-only public artifacts."""

from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
import subprocess
from .config import Config, METHODOLOGY
from .data import hashes, validate, write_csv
from .engine import run, save_state
from .risk import metrics, risk_series, frozen_shocks
from .pricing import option, delta_mapping


def dump(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False)


def code_hash():
    root = Path(__file__).parent
    return sha256(
        b"".join(p.name.encode() + p.read_bytes() for p in sorted(root.glob("*.py")))
    ).hexdigest()


def persist(data, rows, state, root):
    config = state["config"]
    dependencies = {x: version(x) for x in ("numpy", "pandas", "exchange-calendars")}
    identity = {
        "methodology": METHODOLOGY,
        "config": config,
        "inputs": hashes(data),
        "source_hash": code_hash(),
        "dependencies": dependencies,
        "python": platform.python_version(),
        "launch": state["start"],
        "end": state["state"]["date"],
    }
    result_id = sha256(dump(identity).encode()).hexdigest()[:20]
    root = Path(root)
    folder = root / result_id
    financial = dump(rows)
    if folder.exists():
        if (folder / "ledger.json").read_text() != financial:
            raise ValueError("immutable result collision")
        return folder
    root.mkdir(parents=True, exist_ok=True)
    stage = root / (result_id + ".partial")
    if stage.exists():
        raise ValueError("incomplete prior run; inspect .partial before retry")
    stage.mkdir()
    try:
        git = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent,
            ).stdout.strip()
            or None
        )
        manifest = {
            **identity,
            "result_id": result_id,
            "code_version": git,
            "data_mode": data.metadata["mode"],
            "input_coverage": [str(data.prices.index[0].date()), str(data.prices.index[-1].date())],
            "result_coverage": [rows[0]["date"], rows[-1]["date"]],
            "validation": validate(data),
            "financial_hash": sha256(financial.encode()).hexdigest(),
            "owner_review": "pending",
            "public_export": data.metadata["mode"] == "synthetic",
        }
        (stage / "manifest.json").write_text(dump(manifest))
        (stage / "ledger.json").write_text(financial)
        (stage / "metrics.json").write_text(dump(metrics(rows)))
        save_state(state, stage / "state.json")
        write_csv(data, stage / "snapshot")
        stage.rename(folder)
    except Exception:
        shutil.rmtree(stage)
        raise
    return folder


def revision_demo(data, root, baseline_rows, baseline_path):
    from .data import Dataset

    revised = Dataset(
        data.prices.copy(),
        data.rates.copy(),
        dict(data.metadata, revision="synthetic-correction-v2"),
    )
    date = "2020-03-16"
    revised.prices.loc[date, "equity"] *= 1.01
    rows, saved = run(revised)
    folder = persist(revised, rows, saved, root)
    differences = [
        {
            "date": a["date"],
            "index_difference": b["index"] - a["index"],
            "cost_difference": b["cost"] - a["cost"],
            "target_changed": a["instruction"] != b["instruction"],
        }
        for a, b in zip(baseline_rows, rows)
        if a != b
    ]
    report = {
        "mode": "synthetic",
        "corrected_observation": date,
        "change": "equity reinvestment price multiplied by 1.01 for one session",
        "old_result": baseline_path.name,
        "new_result": folder.name,
        "first_affected": differences[0]["date"],
        "last_affected": differences[-1]["date"],
        "max_absolute_index_difference": max(abs(x["index_difference"]) for x in differences),
        "differences": differences,
    }
    return report


def demo(root):
    from .data import synthetic

    data = synthetic()
    baseline, state = run(data)
    start = state["start"]
    path = persist(data, baseline, state, root)
    scenarios = {"baseline_net": (Config(), baseline, path)}
    configs = {
        "baseline_gross": Config(cost_bps=0),
        "equal_net": Config(strategy="equal"),
        "trend_net": Config(strategy="trend"),
        "cash": Config(strategy="cash"),
        "lookback_126": Config(lookback=126),
        "vol_window_126": Config(vol_window=126),
        "reference_6pct": Config(vol_reference=0.06),
        "reference_14pct": Config(vol_reference=0.14),
        "cost_10bps": Config(cost_bps=10),
        "cost_20bps": Config(cost_bps=20),
        "equal_gross": Config(strategy="equal", cost_bps=0),
        "trend_gross": Config(strategy="trend", cost_bps=0),
    }
    for name, cfg in configs.items():
        rows, saved = run(data, cfg, start=start)
        scenarios[name] = (cfg, rows, persist(data, rows, saved, root))
    periods = {
        "full": lambda d: True,
        "development": lambda d: d <= "2016-12-30",
        "held_back": lambda d: d >= "2017-01-03",
    }
    summary = {
        name: {
            "config": asdict(cfg),
            "result_id": folder.name,
            "metrics": {
                period: metrics([r for r in rows if mask(r["date"])])
                for period, mask in periods.items()
            },
        }
        for name, (cfg, rows, folder) in scenarios.items()
    }
    revision = revision_demo(data, root, baseline, path)
    options = []
    for kind in ("call", "put"):
        for vol in (0.15, 0.25, 0.35):
            inputs = {
                "spot": baseline[-1]["index"],
                "strike": baseline[-1]["index"],
                "maturity": 1.0,
                "rate": 0.03,
                "volatility": vol,
                "kind": kind,
                "units": 100.0,
            }
            result = option(**inputs)
            options.append(
                {
                    "inputs": inputs,
                    "result": result,
                    "mapping": delta_mapping(
                        result["delta"], inputs["spot"], baseline[-1]["weights"]
                    ),
                }
            )
    bundle = {
        "mode": "synthetic",
        "methodology": METHODOLOGY,
        "as_of": baseline[-1]["date"],
        "snapshot": hashes(data),
        "coverage": [data.metadata["coverage_start"], data.metadata["coverage_end"]],
        "summary": summary,
        "baseline": baseline,
        "risk": risk_series(baseline),
        "paths": {
            n: [{"date": r["date"], "index": r["index"]} for r in rows]
            for n, (_, rows, _) in scenarios.items()
        },
        "shocks": frozen_shocks(baseline[-1]),
        "revision": revision,
        "options": options,
        "holdout_status": "Retrospective synthetic evaluation; inspected in this delivery; no tuning. No historical holdout inspected.",
    }
    (Path(root) / "demo.json").write_text(dump(bundle))
    (Path(root) / "revision.json").write_text(dump(revision))
    return bundle


def build_site(root, destination):
    root, destination = Path(root), Path(destination)
    bundle = json.loads((root / "demo.json").read_text())
    if bundle["mode"] != "synthetic":
        raise ValueError("public historical export disabled pending rights and owner review")
    # Verify saved financial content before copying anything into a public build.
    for info in bundle["summary"].values():
        folder = root / info["result_id"]
        manifest = json.loads((folder / "manifest.json").read_text())
        if manifest["data_mode"] != "synthetic" or not manifest["public_export"]:
            raise ValueError("non-public result")
        if sha256((folder / "ledger.json").read_bytes()).hexdigest() != manifest["financial_hash"]:
            raise ValueError("financial artifact hash mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    for p in (Path(__file__).parent / "web").iterdir():
        shutil.copy2(p, destination / p.name)
    # Browser only selects precomputed paths/option scenarios, never reruns engine.
    (destination / "data.js").write_text(
        "window.LAB=" + json.dumps(bundle, allow_nan=False, separators=(",", ":")) + ";"
    )
    (destination / "results.json").write_text(dump(bundle))
    (destination / ".nojekyll").touch()
    for name, info in bundle["summary"].items():
        folder = root / info["result_id"]
        shutil.copy2(folder / "manifest.json", destination / (name + "-manifest.json"))
    report = [
        "# Computed synthetic research report",
        "",
        "Software evidence only; no empirical investment evidence.",
        "",
        "All scenarios use common evaluation dates. Figures below include inception costs and pre-inception capital anchor 100.",
        "",
        "|Scenario|CAGR|Volatility|Sharpe|Max drawdown|Total turnover|Costs (index points)|",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, info in bundle["summary"].items():
        m = info["metrics"]["full"]
        sharpe = "N/A" if m["sharpe"] is None else f"{m['sharpe']:.3f}"
        report.append(
            f"|{name}|{m['annual_return']:.2%}|{m['annual_vol']:.2%}|{sharpe}|{m['max_drawdown']:.2%}|{m['turnover_total']:.2f}|{m['cost_index_points']:.4f}|"
        )
    report += [
        "",
        "The sensitivity set is exploratory; no winning parameter is selected. Designed regimes and a chosen universe cannot establish historical profitability.",
        "",
        bundle["holdout_status"],
        "",
        "Daily asset P&L, cash interest, and negative costs are additive index-point attribution. Summing these explains final index minus 100; daily percentages are not presented as compounded attribution.",
        "",
        "Historical stress-window results: unavailable because no historical dataset is licensed or loaded. Frozen-holdings shocks in results.json are hypothetical.",
    ]
    (destination / "research-report.md").write_text("\n".join(report) + "\n")
    return destination
