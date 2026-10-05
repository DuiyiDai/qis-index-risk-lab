"""Extract official H.15 observations offline; does not invent publication dates."""
import argparse
import csv
import hashlib
import io
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SERIES = "RIFSPFF_N.B"
SOURCE = "https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip"


def extract(xml: bytes, start: str, end: str) -> list[dict]:
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("start must precede end")
    matches = [s for s in ET.fromstring(xml).iter()
               if s.attrib.get("SERIES_NAME") == SERIES]
    if len(matches) != 1:
        raise ValueError("expected exactly one business-daily EFFR series")
    rows = []
    previous = None
    for obs in matches[0]:
        if obs.tag.rsplit("}", 1)[-1] != "Obs":
            continue
        day = obs.attrib["TIME_PERIOD"]
        date.fromisoformat(day)
        if previous is not None and day <= previous:
            raise ValueError("duplicate or unordered observation date")
        previous = day
        status, raw = obs.attrib["OBS_STATUS"], obs.attrib["OBS_VALUE"]
        if status == "A":
            value = float(raw)
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("invalid observed rate")
            rate = format(value / 100, ".17g")
        elif status == "ND":
            rate = ""
        else:
            raise ValueError(f"unreviewed observation status: {status}")
        if start <= day <= end:
            rows.append(dict(observation_date=day, status=status,
                             source_percent=raw, rate=rate))
    if not rows:
        raise ValueError("empty requested coverage")
    return rows


def prepare(archive: Path, out: Path, start: str, end: str) -> dict:
    raw = archive.read_bytes()
    with ZipFile(io.BytesIO(raw)) as zipped:
        rows = extract(zipped.read("H15_data.xml"), start, end)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    content = stream.getvalue().encode()
    manifest = {
        "source_url": SOURCE, "series": SERIES, "mode": "historical",
        "requested_coverage": [start, end],
        "actual_observation_coverage": [rows[0]["observation_date"], rows[-1]["observation_date"]],
        "rows": len(rows), "observed": sum(r["status"] == "A" for r in rows),
        "missing_status_rows": sum(r["status"] == "ND" for r in rows),
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "observations_sha256": hashlib.sha256(content).hexdigest(),
        "retrieval_time_evidence": datetime.fromtimestamp(
            archive.stat().st_mtime, timezone.utc).isoformat(),
        "retrieval_time_caveat": "Download completion file mtime; no HTTP receipt preserved.",
        "field": "Effective federal funds annual interest rate; not total return",
        "units": "Percent per annum converted to decimal; 360-day annualization",
        "adjustment": "None; current revised snapshot, not point-in-time release history",
        "rights_source": "https://www.federalreserve.gov/disclaimer.htm",
        "rights_note": "Board information generally public domain subject to exceptions; "
                       "cite Board H.15. This does not grant ETF data rights.",
        "availability": "UNRESOLVED: observation dates are not availability dates. "
                        "H.15 normally releases at 16:15 Eastern, after regular XNYS close. "
                        "Historical publication dates/closures need an explicit policy.",
        "engine_ready": False,
        "accrual_proposal": "Previous-close available rate * calendar days / 360; "
                            "seven-day staleness bound. Not applied by this extractor.",
    }
    artifacts = {"observations.csv": content,
                 "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}
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
    parser.add_argument("archive", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--start", default="2003-12-01")
    parser.add_argument("--end", default="2025-12-31")
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.out, args.start, args.end), indent=2))
