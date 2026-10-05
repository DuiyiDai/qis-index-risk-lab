# Computed synthetic findings

**Synthetic software demonstration, not empirical investment evidence.** QIS-1.0; seed 1729; prices 2004-01-02–2025-12-31; common evaluation 2005-02-01–2025-12-31. Baseline result ID `1fda7c0d81bc2f73d0d6`. Baseline rules and the small sensitivity set were declared before inspecting results; no parameters were selected for performance.

The net overlay's annualized return is 1.96%, compared with 2.05% for the assumed cash account. The overlay therefore does not beat cash on this designed path. Its excess-return Sharpe is 0.010. Cash Sharpe is N/A because its own excess-return variance is zero; cash wealth-return volatility is slightly positive because calendar intervals have different lengths.

The net overlay has 5.39% annualized volatility and -13.89% maximum drawdown, versus 14.23% and -43.23% for the monthly equal-third allocation. Monthly trend without the overlay has 8.05% volatility and -29.88% drawdown. Average risky exposure is 40.02% for the overlay versus 43.45% for monthly trend. Those are outcomes of the chosen regimes and universe, not general estimates of a trend effect.

The overlay's total absolute risky turnover is 38.32 times pre-trade wealth over the full evaluation, with 2.1838 index points of direct fees. Its final net level is 149.9212 versus gross 152.8216. The gross/net ending gap need not equal the sum of fees: earlier fees change later invested wealth and its returns. Turnover includes initial deployment and every daily target restoration, not just month-end signal changes.

## Chronological periods

These are retrospective synthetic periods. The held-back outputs have now been inspected and must not be represented as untouched future evidence.

|Baseline net period|Dates|Annual return|Volatility|Max drawdown|
|---|---|---:|---:|---:|
|development|2005-02-01–2016-12-30|0.76%|5.17%|-13.08%|
|held_back|2017-01-03–2025-12-31|3.56%|5.66%|-13.89%|

The complete predeclared sensitivity table is in `site/research-report.md`; the selector exposes only computed cases. Exploration changes one input at a time, with no best-Sharpe ranking or optimization. Sensitivities cannot resolve universe-selection bias, adjusted-data vintage, execution modelling or sample covariance limitations.

The correction illustration changes one synthetic price on 2020-03-16. Old and new snapshots remain available; `revision.json` reports all affected records. Frozen shocks are instantaneous hypotheticals rather than historical stress episodes. No historical study or historical stress-window comparison can be concluded without permissioned inputs. Data rights, owner understanding and applicable employer requirements remain publication gates.
