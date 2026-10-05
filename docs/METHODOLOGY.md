# Methodology QIS-1.0

See [the pre-evaluation freeze](FREEZE.md) and [the hand-calculated fixture](MINIATURE.md). The code is authoritative for implemented arithmetic; disagreements with this document are bugs, not discretion to change the rules.

## Signals and targets
For reinvestment price Pᵢ,t, trailing return is Pᵢ,t/Pᵢ,t−252 − 1. At an XNYS month-end close, indicator Iᵢ=1 iff this is strictly positive; otherwise zero. Indicators persist between month ends. Base weights bᵢ=Iᵢ/3; inactive allocations remain cash.

Daily returns are Pᵢ,t/Pᵢ,t−1−1, with no implicit filling. Sample covariance over the most recent 63 complete daily observations uses denominator 62. Forecast annual base volatility is √(252 bᵀΣb). Scale=min(1, .10/max(σ,.01)). Risky target w=scale×b and cash=1−Σw. A tiny negative numerical quadratic form is floored at zero before square root. There is no optimizer and no leverage.

Month ends are obtained from the complete exchange-calendar month, not the final observed row. The pinned XNYS calendar is a US exchange-session proxy for the listed ETF sleeves. It handles holidays/exceptional closures, not every possible instrument-specific trading halt. Historical calendar accuracy requires owner review against source coverage.

## Timing and inception
A target decided after close t executes at close t+1. At execution the old reinvestment units earn price changes into t+1. New units earn t+1→t+2. This is implemented by dated instructions in `signals.py` and an explicit predecessor-session lookup in `engine.py`.

Inception is the first session after a qualifying month-end decision with both lookbacks available. Capital of 100 is supplied at that execution close, and initial purchases incur fees immediately. The prior close is a numerical 100 anchor only: no pre-inception price return or cash interest is earned. First-period return includes deployment cost. CAGR uses the actual anchor-to-final calendar interval (including the initial one-session interval). No strategy is launched with insufficient warm-up.

For fair comparisons the generated study forces all scenarios to the baseline inception. This also means the 126-session lookback scenario is not allowed to benefit from launching earlier. The equal-third benchmark is explicitly monthly-rebalanced, not buy-and-hold. The monthly trend comparator does not restore weights between month ends. The overlay restores targets each session after launch, incurring costs even where this merely reverses drift. Cash never trades.

## Self-financing ledger
At each date, qᵢ are existing reinvestment units, C is previous cash, and Δd is actual calendar days. Asset P&L=qᵢ(Pᵢ,t−Pᵢ,t−1). Cash interest=C r_available Δd/360. Let vᵢ=qᵢPᵢ,t and V=Σvᵢ+C+interest.

At a rebalance solve W+cΣ|wᵢW−vᵢ|=V, where c=cost_bps/10,000. The strictly increasing scalar function is solved with 60 bisection iterations on [0,V]. q_new=wᵢW/Pᵢ,t and C_new=(1−Σw)W. Cost=cΣ|wᵢW−vᵢ|. Purchases and sales pay the same rate; cash legs are not separately charged. No trade means existing units remain and weights drift.

Daily wealth change must equal Σasset P&L+cash interest−cost within 1e−9 index points. Tests compare the separate scalar fixed-point reference to 1e−9, and the miniature to 1e−10. The reference does not import the main ledger or cost solver. Signals have separate lag, future-data, calendar and covariance tests; the independent reference checks accounting, not an independently implemented entire strategy.

Absolute risky turnover=Σ|trade notional|/pre-trade wealth, without ½. Summed daily index-point P&L is additive monetary attribution; it is not a sum of compounded percentage contributions. Gross and net are independently rerun holdings ledgers because costs change subsequent investable wealth.

## Cash
Demo cash is an explicitly assumed 2% annual decimal rate, ACT/360 simple accrual between session closes, compounded by carrying earned cash forward. It is not an observed money-market return. A historical run requires official short-rate data, observations and close-availability dates. Latest rate known at the previous valuation close applies for the whole intervening calendar interval; no intraday/weekend revision. A rate cannot be used before its stated availability. Maximum observation age is seven calendar days at interval start; beyond this the calculation stops. Negative rates are deliberately unsupported in the current local contract.

Preferred future source is Federal Reserve H.15 effective federal funds, not a Treasury yield used as bond return. H.15 is posted at 4:15 p.m., after ordinary US equity close. An observation’s date is not its availability date. The provider of a local snapshot must map actual publication timestamps to the first valuation close after release, conservatively accounting for holidays and the observation lag. No historical publication calendar or download adapter has been implemented. EFFR is an interbank overnight rate, not an accessible total-return cash fund; funding/access/compounding mismatches remain. Use ACT/360 as an explicitly assumed accrual convention and record source basis separately.

## Risk and evaluation
CAGR=(last wealth/starting wealth)^(365.25/elapsed days)−1. Annual volatility=sample standard deviation of daily wealth returns×√252. Sharpe=mean(daily return−same-interval cash return)/sample standard deviation of that excess×√252. This conventional approximation does not account for autocorrelation. Zero denominator yields N/A. Drawdown includes the opening capital anchor; subperiods use wealth immediately before that period. Exposures are post-trade fractions.

Trailing risk uses the last 63 wealth returns. Subsequent risk at execution t uses returns t+1 through t+63; its final unavailable windows are null. Forecast target risk belongs to the preceding close’s instruction, not an estimate fitted to those future returns. The synthetic frozen-holdings shocks multiply current component weights by stated instantaneous asset shocks. Replication notionals scale weights by a hypothetical $1m; no share order is implied.

Sensitivity scenarios change one baseline input. Development ends 2016-12-30; held-back evaluation starts 2017-01-03. Both are retrospective synthetic demonstrations, inspected in preparing delivery. No historical results have been examined. Subsequent inspection/reuse must be entered in the review log. No historical stress table is fabricated.

## Option extension
European Black–Scholes uses S,K>0, T≥0, continuous r, assumed σ≥0, zero distributions. d1=[ln(S/K)+(r+σ²/2)T]/(σ√T), d2=d1−σ√T. Call=SΦ(d1)−Ke^(−rT)Φ(d2); put follows the symmetric formula. Delta call=Φ(d1), put=Φ(d1)−1; gamma=φ(d1)/(Sσ√T); vega per percentage point=Sφ(d1)√T/100. Position units multiply every output; one unit pays $1 per index point.

At expiry use intrinsic value; at zero volatility use discounted deterministic payoff. At payoff kinks derivatives are undefined and return null rather than pretend smoothness. Away from kinks gamma and limiting vega are zero. Inputs must be finite; negative rate is supported. Extreme exponent overflow is not a production-hardened domain.

For N-unit delta Δ (already position-scaled), frozen risky replication dollars are ΔS wᵢ; an offsetting hedge is −ΔS wᵢ. Example: delta +60 dollars/point, S=100, equity weight 1/3 gives +$2,000 replication equity exposure; a local offset is −$2,000. The latter is an illustration, not a shorting feature of the index. Dynamic allocations, vega, jumps, costs and liquidity invalidate a claim of perfect ETF replication.
