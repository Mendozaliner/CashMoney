# ROADMAP (reprioritized 2026-07-14 s6)

0. **Universe expansion landed 2026-07-14**: EFA, EEM, AGG, DBC, VNQ added to
   the nightly data pipeline (first fresh cache after the next Action run).
   Once cached: re-register TRUE Antonacci GEM (SPY vs EFA/EEM vs SHY) and
   TRUE Faber GTAA-5 (SPY/EFA/IEF/VNQ/DBC) as new experiments — these were
   previously blocked by the US-only universe. Watch histories: EFA 2001+,
   EEM/AGG 2003+, VNQ 2004+, DBC 2006+.

1. **Criterion-1 significance on v2** — bootstrap diff-vs-SPY on the FULL
   2000-2025H walk-forward sample (not just the 2020+ fold). Larger n may
   clear the noise band. Pure analysis, no new configs.
2. **GTAA ensemble feasibility memo** — correlation of GTAA(w150,b0) daily
   returns vs v2 across folds, using existing E6 runs (no new configs).
   If weakly correlated, register a combined-sleeve test (equal-risk weights).
3. **Vol targeting ON the GTAA sleeve** (≤6 cfg, separate registration) —
   only if #2 shows low correlation; else skip to fractional Kelly.
4. **Sector momentum + trend gate** — retry E5 with individual-sector SMA200
   filter: a sector must be above its own 200-day MA to qualify for top-N.
   Addresses the momentum-crash problem (XLK above SMA200 entering dot-com peak
   would gate it out). 4 configs max.
5. **Criterion-1 significance gap**: v2-minus-SPY bootstrap on full 2000-2025H
   walk-forward (not just the 2020+ fold). The sample is larger; may clear the
   noise band. Revisit again after a second sleeve enables ensemble test.
6. **Position sizing**: fractional Kelly on champion (Phase-3 material).
7. **VIX term-structure data** (spot VIX failed E2; futures term structure
   needed — pipeline doesn't carry it yet).

## Negative results (do NOT re-test in the original form)
- Dual Momentum with SHY harbor (E7, s6): mean WF Sharpe 0.539, DD -36.7%.
  The SPY/QQQ/DIA rotation whipsaws regardless of harbor. Family closed.
- Kill-switch on v2 at ANY setting — tight -12/-15 (E4) and loose -20/-10
  (E8, s6) both failed: no DD improvement, Sharpe cost. Closed permanently.
- Faber GTAA as a STANDALONE champion (E6, s6): fails significance vs SPY
  (DSR 0.897). NOT closed as an ensemble component — see watch-list.
- Raw daily SMA crossover (band=0); 50d SMA windows (noise).
- Vol targets ≤0.12 on trend-gated SPY (over-delever; Sharpe 0.69-0.76).
- Wider vol targets 0.21-0.30: flat surface, no gain over v2 (E1, 2026-07-14).
- Spot-VIX percentile de-risking overlays on v2, scale {0.5, 0}, pct {70,80,90}:
  failed DD/DSR/CI bars (E2, 2026-07-14). High VIX precedes high returns.
- Dual Momentum (Antonacci GEM) with TLT as defensive harbor: failed all bars
  (E3, s5). TLT harbor catastrophic in 2022 rising-rate regime. Revisit with SHY.
- Kill-switch at kill_dd {-0.12,-0.15}: parameters too tight, whipsaw cost > DD
  benefit (E4, s5). Retry at -20%/-10%.
- Cross-sectional sector momentum (top-N XL*, lookback 12-1mo): failed all bars
  (E5, s5). Momentum crash in 2000-09 fold. Retry with sector-level trend gate.
