"""Generate a short interpretation from frozen outputs; no engine changes."""

import json
from pathlib import Path

b = json.loads(Path("results/synthetic/demo.json").read_text())
s = b["summary"]
a = s["baseline_net"]["metrics"]["full"]
e = s["equal_net"]["metrics"]["full"]
t = s["trend_net"]["metrics"]["full"]
c = s["cash"]["metrics"]["full"]
g = s["baseline_gross"]["metrics"]["full"]
text = f"""# Computed synthetic findings

**Synthetic software demonstration, not empirical investment evidence.** QIS-1.0; seed 1729; prices {b["coverage"][0]}–{b["coverage"][1]}; common evaluation {a["start"]}–{a["end"]}. Baseline result ID `{s["baseline_net"]["result_id"]}`. Baseline rules and the small sensitivity set were declared before inspecting results; no parameters were selected for performance.

The net overlay's annualized return is {a["annual_return"]:.2%}, compared with {c["annual_return"]:.2%} for the assumed cash account. The overlay therefore does not beat cash on this designed path. Its excess-return Sharpe is {a["sharpe"]:.3f}. Cash Sharpe is N/A because its own excess-return variance is zero; cash wealth-return volatility is slightly positive because calendar intervals have different lengths.

The net overlay has {a["annual_vol"]:.2%} annualized volatility and {a["max_drawdown"]:.2%} maximum drawdown, versus {e["annual_vol"]:.2%} and {e["max_drawdown"]:.2%} for the monthly equal-third allocation. Monthly trend without the overlay has {t["annual_vol"]:.2%} volatility and {t["max_drawdown"]:.2%} drawdown. Average risky exposure is {a["mean_risky_exposure"]:.2%} for the overlay versus {t["mean_risky_exposure"]:.2%} for monthly trend. Those are outcomes of the chosen regimes and universe, not general estimates of a trend effect.

The overlay's total absolute risky turnover is {a["turnover_total"]:.2f} times pre-trade wealth over the full evaluation, with {a["cost_index_points"]:.4f} index points of direct fees. Its final net level is {a["final_index"]:.4f} versus gross {g["final_index"]:.4f}. The gross/net ending gap need not equal the sum of fees: earlier fees change later invested wealth and its returns. Turnover includes initial deployment and every daily target restoration, not just month-end signal changes.

## Chronological periods

These are retrospective synthetic periods. The held-back outputs have now been inspected and must not be represented as untouched future evidence.

|Baseline net period|Dates|Annual return|Volatility|Max drawdown|
|---|---|---:|---:|---:|
"""
for name in ["development", "held_back"]:
    m = s["baseline_net"]["metrics"][name]
    text += f"|{name}|{m['start']}–{m['end']}|{m['annual_return']:.2%}|{m['annual_vol']:.2%}|{m['max_drawdown']:.2%}|\n"
text += """
The complete predeclared sensitivity table is in `site/research-report.md`; the selector exposes only computed cases. Exploration changes one input at a time, with no best-Sharpe ranking or optimization. Sensitivities cannot resolve universe-selection bias, adjusted-data vintage, execution modelling or sample covariance limitations.

The correction illustration changes one synthetic price on 2020-03-16. Old and new snapshots remain available; `revision.json` reports all affected records. Frozen shocks are instantaneous hypotheticals rather than historical stress episodes. No historical study or historical stress-window comparison can be concluded without permissioned inputs. Data rights, owner understanding and applicable employer requirements remain publication gates.
"""
Path("docs/RESEARCH_FINDINGS.md").write_text(text)
print("docs/RESEARCH_FINDINGS.md")
