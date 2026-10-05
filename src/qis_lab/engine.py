from dataclasses import asdict
from hashlib import sha256
import json
import pandas as pd
from .config import Config
from .data import validate, frame_bytes, rate_at
from .signals import decisions
from .ledger import State, step


def prefix_hash(data, date):
    return sha256(
        frame_bytes(data.prices.loc[:date]) + frame_bytes(data.rates.loc[:date])
    ).hexdigest()


def run(data, config=Config(), start=None, stop=None, saved=None):
    validate(data)
    p = data.prices
    instructions = decisions(p, config)
    eligible = [x["execution_date"] for x in instructions.values() if x["execution_date"]]
    if not eligible:
        raise ValueError("insufficient warm-up: no eligible execution")
    start = start or eligible[0]
    if start < eligible[0] or pd.Timestamp(start) not in p.index:
        raise ValueError("start must be an eligible session after warm-up")
    # Explicit common start must correspond to an instruction (monthly comparators too).
    j0 = p.index.get_loc(pd.Timestamp(start))
    if str(p.index[j0 - 1].date()) not in instructions:
        raise ValueError("start has no preceding decision")
    if saved:
        if saved["config"] != asdict(config) or saved["start"] != start:
            raise ValueError("saved configuration/start mismatch")
        if saved["prefix_hash"] != prefix_hash(data, saved["state"]["date"]):
            raise ValueError("saved input prefix changed; create a revision")
        state = State(**saved["state"])
        begin = p.index.get_loc(pd.Timestamp(state.date)) + 1
    else:
        anchor = p.index[j0 - 1]
        state = State(str(anchor.date()), [0.0, 0.0, 0.0], 100.0, 100.0, p.iloc[j0 - 1].tolist())
        begin = j0
    rows = []
    for j in range(begin, len(p)):
        date = p.index[j]
        if stop and date > pd.Timestamp(stop):
            break
        decision_date = str(p.index[j - 1].date())
        instruction = instructions.get(decision_date)
        state, row = step(
            state,
            date.date(),
            p.iloc[j].to_numpy(),
            rate_at(data, p.index[j - 1]) if j != j0 else 0.0,
            instruction,
            config.cost_bps,
        )
        # Initial capital arrives at execution close: no pre-inception interest.
        rows.append(row)
    saved = {
        "config": asdict(config),
        "start": start,
        "state": asdict(state),
        "prefix_hash": prefix_hash(data, state.date),
    }
    return rows, saved


def save_state(saved, path):
    from pathlib import Path

    Path(path).write_text(json.dumps(saved, sort_keys=True, indent=2))
