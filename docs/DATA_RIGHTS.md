# Sources, data contract and rights review
Reviewed 2026-10-05. An official H.15 cash-rate archive was downloaded and extracted locally. No ETF market-price dataset or historical strategy result exists. Source pages are referenced, not bundled. This is a record of observed terms and unresolved questions, not legal approval.

## Candidate instruments (issuer definitions verified)
- [SPY issuer](https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy): USD S&P 500 equity exposure; inception January 22, 1993. This is a large-cap US proxy, not the complete US stock market.
- [IEF issuer](https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf): USD US Treasury securities with remaining maturities seven to ten years; launched July 22, 2002. It has duration risk; it is not cash.
- [GLD issuer](https://www.ssga.com/us/en/institutional/etfs/spdr-gold-shares-gld): gold bullion price exposure less trust expenses, USD listing; issuer reports November 18, 2004 inception/listing. Trust legal formation dates in older documents differ; use the first actual listed history for price validation.

These are candidate proxies only. Synthetic columns are generic sleeves, not generated SPY/IEF/GLD prices. No substitution is automatic. All historical prices must be compatible total-return reinvestment series. Do not add dividends or deduct embedded expense ratios again. Reinvestment units are not executable ETF shares. A currently adjusted history does not establish a point-in-time vintage.

## Permission status
|Source|Automated access|Local research / AI processing|Derived public charts|Raw redistribution|Decision|
|---|---|---|---|---|---|
|Generated synthetic fixtures|Offline generation|Project-generated|Permitted project outputs|Permitted project outputs|Used|
|Yahoo|Express prior authorization is required by the reviewed regional terms for automated collection|No project-specific permission established; AI workflow rights unresolved|Not established|Not established|Not selected; no adapter|
|Federal Reserve Board H.15|Official archive downloaded; offline extractor implemented|Board notice generally permits reuse subject to exceptions and attribution|Subject to Board notice|Subject to Board notice|Real observations extracted privately; explicit modeled availability implemented; actual historical publication times unverified|
|Issuer fact pages|Used for definitions, not time-series acquisition|No permission to process full historical feeds inferred|Historical series rights unresolved|Not established|Definitions only|
|FRED / Stooq|Not selected|Not evaluated or assumed unrestricted|Not established|Not established|No adapter|

[Yahoo terms reviewed](https://legal.yahoo.com/ca/en/yahoo/terms/otos/) prohibit automated collection without express prior permission. The requested US terms URL was unavailable in browsing; the Canadian regional page is not a determination of which agreement applies to this owner. [Yahoo API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apitnc/index.html) separately restrict API data use. Public accessibility does not resolve local research, chart publication, raw redistribution or AI-assisted processing rights. No Yahoo API, scraping or paid service is used.

[Federal Reserve H.15](https://www.federalreserve.gov/releases/h15/) states daily 4:15 p.m. publication excluding closures/holidays; rates are percent per annum and series footnotes differ. [About the release](https://www.federalreserve.gov/releases/h15/about.htm). The official DDP archive link was verified and downloaded on 2026-10-05; the offline extractor preserves missing-status observations and hashes. The separate map_cash_availability.py creates rates.csv under an explicitly assumed conservative release calendar; see CASH_AVAILABILITY.md. [Board usage notice](https://www.federalreserve.gov/disclaimer.htm) generally places Board information in the public domain, with non-Board exceptions. This is not blanket permission for every linked provider. Logos are not used.

## Local CSV adapter
A folder contains:

1. `prices.csv`: `date,equity,treasury,gold` with ISO dates, one row for every expected XNYS session in declared coverage. Values are positive finite USD reinvestment prices. Expected coverage is declared independently in metadata; absent first/last or interior sessions all fail. No inner join or fill.
2. `rates.csv`: `available_date,observation_date,rate`. Availability is the first valuation close at which the observation is known. Decimal annual rate, not percentage points (2%=0.02). Sorted and unique availability dates; no observation after availability. Latest available observation carries at most seven calendar days from observation at interval start. Multiple releases before the same close must be explicitly consolidated upstream to the last available observation; no silent duplicates.
3. `metadata.json`: mode, coverage_start/end, cash_kind, per-instrument metadata, permissions, snapshot hashes. See `fixtures/historical-metadata.template.json`; placeholders deliberately cannot validate. Source/retrieval/availability/adjustment/rights must be documented per instrument. Rate metadata must document official source, source annualization, observation lag and availability mapping. All price observation dates live in CSV; rates carry both dates.

Canonical snapshot hashes are SHA-256 of `frame_bytes` in `data.py` (17 significant digits and ISO dates). After reading prices/rates use `hashes(dataset)` to compute expected canonical hashes; these differ from arbitrary externally formatted raw bytes. Keep original vendor files separately and record original-file hashes in metadata. Manifest records canonical prices, rates and metadata hashes.

Historical commands require declared local-research, automated-processing and AI-assisted-processing permission, but a boolean is not legal evidence: attach terms/license identifiers and owner review. Public historical export is disabled in this version even if metadata requests it. Inputs and historical outputs stay in ignored private folders. No network refresh command exists. Missing access remains a blocker rather than triggering an unauthorized downloader.

## Primary conceptual / software references
- [Moskowitz, Ooi and Pedersen, Time Series Momentum (2012)](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum): own-past-return trend motivation. This ETF long/cash rule differs from the paper’s futures/forward excess-return implementation. Link only; do not redistribute the document.
- [S&P, target-volatility discussion (2024)](https://www.spglobal.com/spdji/en/education/article/impact-of-target-volatility-levels-in-volatility-controlled-indices/): risk control intuition. This project forbids the leverage some indices allow; no published methodology is replicated.
- [NumPy covariance](https://numpy.org/doc/stable/reference/generated/numpy.cov.html), [pandas return changes](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html), [exchange_calendars](https://github.com/gerrymanoim/exchange_calendars), [pytest](https://docs.pytest.org/en/stable/), [Ruff](https://docs.astral.sh/ruff/): checked primary documentation before implementation. Tested versions are pinned; latest documentation may describe newer versions.
- [QuantLib documentation](https://www.quantlib.org/docs.shtml): reviewed as a pricing-library reference. QuantLib is not installed or used for cross-checks; actual checks here are parity, limits and finite differences. No QuantLib validation is claimed.
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages): static HTML/CSS/JavaScript hosting. No Python backend runs in Pages. Publishing is not performed by this project’s CI.

## Historical acquisition update
The offline `scripts/prepare_official_cash.py` extracted 5,552 valid EFFR observations and 211 ND rows for 2003-12-01 through 2025-12-31. The source annualization is 360 days. An explicit conservative availability mapping is implemented and tested; historical actual release timestamps remain unverified. Observation dates are not release dates. The current snapshot is not a point-in-time archive. No historical strategy results have been computed.

[Tiingo terms](https://app.tiingo.com/tos/) prohibit persistent storage on Starter/Trial; paid retention is conditional. [Alpha Vantage documentation](https://www.alphavantage.co/documentation/) marks Daily Adjusted Premium. Neither provider was selected or purchased. A suitable existing account or explicit supplier license is still needed for the ETF inputs.
