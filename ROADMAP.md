# ROADMAP (reprioritized 2026-07-14 s5)

1. **Trend-following across multiple assets (Faber GTAA)** — NEW SLEEVE.
   SPY + IEF + GLD + IWM each independently gated on their own SMA200; hold
   equal-weight subset with trend-on; rest in T-bills. Key improvement over
   Dual Momentum: no forced bond-as-safe-haven. Pre-register with DSR ≥ 0.95
   bar; own $1k sub-portfolio if it clears.
2. **Refined Dual Momentum (SHY defensive, not TLT)** — revisit with reduced
   duration risk. Replace TLT with SHY (3-month T-bills) as the defensive harbor.
   The 2022 TLT crash killed the vanilla GEM. Hypothesis: SHY defensive + US
   absolute momentum (SPY/QQQ vs SHY) avoids the bond-duration problem.
3. **v2 + conservative kill-switch (-20%/-10%)** — retry E4 at kill level
   BELOW v2's worst-fold DD (-20.5%), so it fires only in GFC/COVID scenarios.
   Pre-register separately; 2 configs only.
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
