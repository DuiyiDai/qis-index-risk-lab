# Executed validation record

Local execution on 2026-10-04. Python 3.11.11 on macOS; exact installed dependencies recorded in `requirements-lock.txt`. No hosted GitHub Actions run is claimed. The CI workflow is prepared and contains no publishing step.

## Commands actually executed

|Command / check|Outcome|
|---|---|
|Install pinned dependencies and editable package with uv into workspace-local venv|Succeeded; 17 dependencies and project installed|
|`pytest -q` (final expanded suite)|**41 passed in 16.35 seconds**; test fixture rejects socket connections|
|`ruff check src tests scripts`|All checks passed|
|`ruff format src tests` and script formatting|Executed|
|`qis-lab demo`|Succeeded; 13 scenarios plus a preserved correction result|
|`qis-lab build-site`|Succeeded; local `site/` built from synthetic results|
|`qis-lab validate results/synthetic/1fda7c0d81bc2f73d0d6/snapshot`|Passed; 5,535 expected XNYS sessions|
|`qis-lab historical` with that synthetic snapshot|Failed **as intended**: historical command rejects synthetic inputs; no historical result created|
|Manifest source-hash check against current Python modules|Matched baseline result `1fda7c0d81bc2f73d0d6`|
|`python scripts/research_note.py`|Generated computed narrative and period table in `docs/RESEARCH_FINDINGS.md`|
|Headless installed Google Chrome via local Playwright|Passed desktop 1440×1100 and mobile 390×844 checks; no page errors or page horizontal overflow|
|Browser selections|13 scenario options, 5,263 audit dates, six option cases; checked held-back date range, Jan 31→Feb 3 timing and correct sleeve-to-target display mapping|
|Desktop/mobile full-page render inspection|Rendered and visually inspected; no clipped sections observed|
|`git init` and `git check-ignore`|Local empty repository initialized; private-delivery, private-data and private-results patterns confirmed ignored. Nothing committed, pushed or deployed|

The browser test was run using an already installed local Playwright package and an isolated headless Chrome profile. It is not a pinned runtime dependency or claimed hosted browser CI. Initial attempts found no downloaded Playwright browser and hit a local browser sandbox restriction; the successful run used installed Chrome with approved local execution. One test harness read of a collapsed `<details>` element was corrected from visible text to text content. No application failure was concealed.

The first numerical test run caught a shared pandas index-name bug in CSV export (30 passed, one failed). Independent index copies corrected the date-column name. The final suite includes that CSV round-trip regression. Additional tests were then added for lifecycle, metrics and contract failures. No baseline parameters were changed after evaluation.

## Numerical coverage
- Calendar-derived month ends, truncated endpoints, missing/duplicate/unordered/nonpositive/nonfinite prices.
- Warm-up refusal, zero/near-zero forecast volatility, capped weights, invalid configuration and target failures.
- Explicit decision/execution lag, future prices and future rates unable to change past numerical output.
- Inception/rebalance costs, drift, fully invested post-cost purchases, all-cash behavior and three-day interest.
- Daily wealth/P&L identity; independent fixed-point reference versus bisection ledger; zero-cost valuation consistency.
- Identical financial reruns and CSV round trips; JSON-state incremental replay exactly equal to batch; modified prefix rejected.
- Preserved correction versions, unchanged earlier results, different result IDs, idempotent save and collision failure.
- Direct sample-covariance calculation, subsequent realized-risk alignment, N/A cash Sharpe, hypothetical shock arithmetic.
- Rate availability/staleness boundaries, duplicate/missing rate dates, historical permission/inception/hash gates. Historical-schema tests use explicitly artificial fixtures and never persist them as historical results.
- Option parity/bounds, expiry/zero-volatility limits, finite-difference delta/gamma/vega, signed position scaling and hedge direction.

The miniature tolerance is 1e−10 index points; multi-day reference comparison 1e−9. Daily ledger reconciliation stops beyond 1e−9. Replay and deterministic-run checks use exact equality in the pinned local environment. Cross-platform floating-point bit identity is not promised.

## Actual generated coverage
Synthetic prices: 2004-01-02–2025-12-31 (5,535 sessions). Evaluation: 2005-02-01–2025-12-31 (5,263 rows), with prior-close 100 capital anchor and inception costs. Historical ETF observations: **none**. Official cash-rate observations were subsequently acquired; see the 2026-10-05 update below. Correction: one synthetic equity price on 2020-03-16; affected records continue through 2025-12-31. Both original and corrected snapshots remain saved.

## Not tested or completed
No successful real historical ingestion, authorized download adapter, provider API contract, archived publication-time database, market-data license approval, QuantLib external oracle, production numerical extremes, real execution, live market comparison, assistive-technology audit, deployment or hosted CI run. See `LIMITATIONS.md`. Human financial review, data-rights review and applicable employer review remain pending.


## 2026-10-05 official-cash integration update

Executed locally with the same pinned environment:

- `python -m pytest -q`: **58 passed in 14.74 seconds**, including offline XML extraction and availability/integration tests.
- `ruff check src tests scripts`: all checks passed.
- `python scripts/map_cash_availability.py private-data/official-cash/extracted-v1 private-data/official-cash/availability-v1`: succeeded, then successfully repeated against the same output directory without overwriting different content.
- Real cash snapshot validation: 5,313 valuation closes, maximum observation age six days, 5,507 selected available-rate rows including earlier warm-up. All output hashes recorded.

This is rate-input preparation under an explicit modeled publication schedule, not a completed historical strategy run or a verified historical publication archive. No asset-price placeholders, historical strategy performance, public historical exports or parameter changes were introduced. Tests for missing actual historical releases cannot substitute for archived release evidence.
