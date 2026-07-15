# Research notes — Trend-gated naive risk parity (session 8, 2026-07-15)

Roadmap item #5: allocate across SPY / IEF / GLD with weights proportional to
inverse realized volatility, keeping v2's trend gate (asset included only when
above its long-term SMA); excluded weight sits in T-bills.

## Sources (web pass, 2026-07-15)
1. Asness, Frazzini & Pedersen (2012), "Leverage Aversion and Risk Parity" —
   levered inverse-vol portfolios beat 60/40 on Sharpe over long samples;
   unlevered, the raw return is LOW (the classic risk-parity trade-off).
2. Maillard, Roncalli & Teiletche (2010), "Equally-Weighted Risk Contribution
   Portfolios" (CERP WP 142/14 mirror) — ERC sits between min-variance and
   equal-weight; with correlations ignored, 1/vol ("naive RP") is the 2-asset
   special case and a reasonable N=3 approximation when correlations are low.
3. "Risk Without Return" (arXiv 1307.0114) — critique: RP's historical edge is
   substantially a levered-bond carry story; beware extrapolating the 1981-2021
   bond bull into the future.
4. ReSolve, "Risk Parity: Methods and Measures of Success" — inverse-vol vs ERC
   vs equal-risk-budget comparisons; naive 1/vol competitive at low N.
5. Allocate Smartly, "TAA Strategy Combining Risk Parity & Trend Following"
   (Keuning/Keller) — trend gate + RP sizing is one of the lowest-vol TAA
   strategies tracked; OOS decay vs paper results is material.
6. CXO Advisory, "Combining Trend Following and Risk Parity across Asset
   Classes" — full RP (with correlations) beat plain inverse-vol 1.48 vs 1.31
   gross Sharpe in the study's long-short setting; costs/complexity higher.
7. MPI / CAIA + Neuberger Berman on 2022 — RP's bond overweight was the failure
   mode when stock/bond correlation flipped positive (+0.65 in 2022); RP
   benchmark fell ~-27%. A per-asset trend gate is our specific countermeasure:
   IEF was below trend for most of 2022 and would have sat in cash.

## Design (max 2 tunable params)
- Universe: SPY, IEF, GLD (equity / duration / inflation hedge). GLD starts
  2004-11, IEF 2002-07 -> fold 1 truncated to ~2004-2009 for the full trio;
  missing-history slots sit in cash (same convention as GTAA E6/E10).
- Monthly decision (month-end), held one month, multi_engine shift(2) timing.
- w_i = (1/vol_i) / sum_all(1/vol_j), so the vol budget is set across the FULL
  panel; assets failing their SMA200*(1+band) gate are zeroed (weight -> cash).
  This keeps the de-risking property (gate off = less invested, not
  renormalized into the survivors).
- Params: vol lookback {20, 60, 120} x trend band {0.00, 0.03}; SMA window
  fixed at 200 (v2 convention). Grid = 6.

## Skeptical prior
Unlevered RP on 3 assets is likely to LAG SPY badly on raw return (sources 1,
3); the only path to adoption is a large Sharpe/DD improvement that clears the
DSR and diff-CI gates — which nothing has cleared yet in 94 prior configs.
GTAA-5 (E10) already achieved DD -9.9% and still failed significance.
