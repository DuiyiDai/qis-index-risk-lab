# Official cash observations and modeled availability

Policy H15-CONSERVATIVE-CALENDAR-1, declared 2026-10-05 before any ETF historical strategy evaluation. This supplements QIS-1.0's cash convention without changing signals, allocation rules or holdout periods. No historical strategy performance has been inspected. Outputs are private and separate from the synthetic site.

## Evidence and assumption

The [Board H.15 release](https://www.federalreserve.gov/releases/h15/) gives a normal 16:15 Eastern publication time on release weekdays, excluding holidays and Board closures; EFFR is quoted on a 360-day annual basis. The current release displays earlier observation dates. We have a current revised snapshot, not an archive of first-published values or historical release timestamps. The [NY Fed reference-rate information](https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates) describes next-business-day EFFR publication; the Board release is the data source used here.

The project chooses a deliberately delayed research convention:

1. For each observed rate dated D, take the next date strictly after D that is both an XNYS session and not a holiday in pandas USFederalHolidayCalendar.
2. Assume publication at 16:15 America/New_York on that date. Convert to UTC with the timezone database, including daylight saving.
3. The rate becomes usable at the first actual XNYS session close strictly after that assumed timestamp. An early close cannot accidentally use a later publication.
4. If multiple observations first become usable at the same close, select the latest observation. Preserve every candidate and its selection flag in availability_audit.csv.
5. At each starting close, carry the latest eligible observation only while its age is at most seven calendar days. Missing source weekdays, missing initial history, invalid values and stale rates stop the calculation. Original ND rows are retained in the input and never converted into zero-rate observations.

The joint-calendar rule intentionally delays some releases beyond their likely actual publication (for example when banks operate but the stock exchange is closed). It does not prove availability during unrecorded exceptional Board closures, release delays or subsequent revisions. This is an explicit assumption for retrospective research, **not a verified point-in-time database**. The manifest sets availability_is_assumed=true and point_in_time_verified=false. Changing this convention requires a new policy/result version, not editing a saved snapshot.

## Dated example and accrual

A Thursday 2025-01-02 observation is assigned an assumed Friday 2025-01-03 16:15 Eastern release and Monday 2025-01-06 close availability. It can first set interest for the interval beginning at that Monday close. It does not earn the Friday-to-Monday interval retrospectively.

For a hand-check with a **synthetic** available annual rate of 3.6%, cash of 100 at Friday 2025-01-17 accrues through Tuesday 2025-01-21 across four calendar days: 100 × .036 × 4 / 360 = .04. No separate holiday or cash-leg trading fee applies. Tests exercise this through the existing ledger. The example rate is not asserted to be the observed rate on those dates.

EFFR is an overnight interbank proxy; these accruals are hypothetical, not an investable cash fund total return. No deposit spread, tax or fee is modeled. Source methodology changed in 2016; that and vintage revisions remain data limitations.

## Local commands and output

After installing the pinned project environment, from the project root:

```sh
python scripts/prepare_official_cash.py private-data/official-cash/FRB_h15_xml.zip private-data/official-cash/extracted-v1
python scripts/map_cash_availability.py private-data/official-cash/extracted-v1 private-data/official-cash/availability-v1
pytest -q
ruff check src tests scripts
```

Both scripts are offline. The original official archive remains untouched. The extractor's engine_ready=false records that raw observation dates alone are insufficient; the separate availability output adds the explicit policy. rates.csv has the engine's available_date,observation_date,rate schema. It still requires compatible licensed prices and complete metadata to form a historical strategy input. No placeholder asset prices are generated.

The mapping command was executed on the real frozen snapshot: 5,507 available-rate rows (including earlier cash warm-up), 5,313 checked closes from 2004-11-18 through 2025-12-31, maximum observation age six calendar days. availability_audit.csv also retains observations whose assumed availability is beyond the requested end date; those are excluded from rates.csv. All output files are hashed in manifest.json; identical reruns are accepted, changed outputs cannot overwrite existing versions.

Tests use synthetic rate fixtures and no network: publication lag, January 2025 funeral closure, a federal holiday while XNYS is open, daylight saving, future perturbation, explicit consolidation, calendar-day ledger accrual, missing source weekdays, invalid ND filling, staleness, missing initial data, CSV integration, hashes and immutable replay. Actual historical publication timestamps and provider license decisions are not validated by these tests.
