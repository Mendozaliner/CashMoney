# ROADMAP (reprioritized 2026-07-15 s7)

0. ~~Universe expansion~~ DONE s7: EFA, EEM, AGG, DBC, VNQ tested.
   ~~TRUE Antonacci GEM~~ DONE (E9, DISCARDED). ~~TRUE Faber GTAA-5~~ DONE (E10,
   DISCARDED on significance — added to watch-list for revisit when DBC has more history).

1. ~~Criterion-1 significance on v2~~ DONE s6b: full-sample diff CI
   [-0.009, +0.708] — misses zero by 0.009. Not passed.

2. ~~GTAA ensemble feasibility memo~~ DONE s7 (M1): correlation 0.721 —
   above 0.70 threshold. 50/50 ensemble OOS Sharpe 0.946 but $1k = $6,542
   vs v2 $9,258 (raw return drag too large). ENSEMBLE NOT RECOMMENDED at
   current correlation. Only revisit if a new sleeve with corr < 0.50 to v2 emerges.

3. ~~Vol targeting ON GTAA sleeve~~ CLOSED (correlation too high; ensemble not viable).

4. ~~Sector momentum + trend gate~~ DONE (E11, s7, DISCARDED). Trend gate did NOT
   fix E5: worst DD still -47.4%. Sector family PERMANENTLY CLOSED (both E5 and E11
   failed; further sector rotation is excluded from the research agenda).

5. ~~Risk Parity SPY/IEF/GLD~~ DONE s8 (E12, DISCARDED on diff-CI; first-ever
   DSR pass at 0.982, worst DD -7.6%, corr to v2 0.467 — watch-listed).
   Ensemble revisit condition (corr < 0.50) was consumed the same session:
   ~~v2/RP ensemble~~ DONE s8 (E13, DISCARDED — CI straddles zero, raw terminal
   lags SPY). Do NOT re-tune mixture weights; see watch-list conditions.

6. **Momentum + Value tilt on sector basket**: overlay a simple price-to-earnings
   or price-to-book screen on top of sector momentum. Requires fundamentals data
   not yet in the pipeline. FLAG: fundamentals data source needed first.

7. **Fractional Kelly position sizing** on champion v2 (Phase-3 material).
   Only attempt after Criterion-1 significance is passed.

8. **VIX term-structure data** (spot VIX failed E2; futures term structure
   needed — pipeline doesn't carry it yet). Not a priority until Phase-3.

9. **Live track maturation**: accumulate 3 consecutive months of v2 outperforming
   SPY live (0/3 months as of 2026-07-15). No research action — just wait and mark
   monthly. First check: ~2026-08-13.

10. **v2 full-sample significance re-check (monthly)**: the s6b diff-vs-SPY CI
    missed zero by 0.009. Each month of fresh live data extends the sample; re-run
    the full-sample CI on the first session after each data-month completes.
    Cheap, no new configs, directly attacks criterion 1. Next: early August 2026.

11. ~~Harry Browne Permanent Portfolio~~ DONE s9 (E14, DISCARDED — CI straddles zero,
    terminal lags; WATCH-LISTED with DSR 0.975, corr 0.430, DD -15.82%).
12. ~~Blended Multi-Lookback Momentum~~ DONE s9 (E15, DISCARDED — high corr 0.879 to v2,
    blended composite dilutes the binary SMA200 gate without adding value). Family CLOSED.
13. ~~Adaptive Asset Allocation (top-N + min-var)~~ DONE s9 (E16, DISCARDED — DD -47.6%,
    same momentum-crash failure as E5 sector rotation; momentum without trend gate fails
    in bear markets). Family CLOSED.

## Priority order for next sessions
1. (#9) Live-track marks — highest priority for Phase-2 graduation (just wait + mark)
2. (#10) Monthly v2 full-sample significance re-check — first week of August (s6b CI
   missed zero by 0.009; each live data month extends the sample)
3. (#6) Value tilt — blocked on fundamentals data pipeline; research queue otherwise
   EXHAUSTED pending live data (135 configs burned; 4 families permanently closed:
   sector, kill-switch, blended-mom, AAA). Prefer NO new families over re-tuning.

## Negative results (do NOT re-test in the original form)
- **Harry Browne Permanent Portfolio PP(band=0.10)** (E14, s9): DSR 0.975 (passes),
  corr 0.430 to v2 (low), DD -15.82% (best ever). Failed CI [-0.575,+0.901]; terminal
  $4,308 << v2 $9,294. Raw-return giveaway in bull markets. Watch-listed (not closed).
- **Blended multi-lookback momentum** (E15, s9): composite of 3+12 or 1+3+6+12 month
  momentum signals. DSR 0.981, DD -18.15%, but CI straddles zero and corr 0.879 with v2 —
  near-duplicate. The BINARY SMA200 gate is strictly better than a graded composite for
  risk-off decisions. Family CLOSED — do not retry multi-lookback composites.
- **Adaptive Asset Allocation top-N/min-var** (E16, s9): momentum selection + minimum-
  variance weights on SPY/IWM/EFA/IEF/GLD/DBC. DD -47.6% (worst ever for multi-asset),
  DSR 0.918. Without a trend gate, momentum-picked portfolios crash as badly as sector
  rotation. Adding correlation-aware weights doesn't fix the timing problem. Family CLOSED.
- **Trend-gated naive risk parity SPY/IEF/GLD** (E12, s8): best lb60/b0.03 —
  mean WF 1.018, DD -7.6%, DSR 0.982 (passed), but diff-vs-SPY CI straddles zero
  and $1k terminal $2,995 vs SPY $6,768. NOT closed — watch-listed (see STATE.md);
  no standalone re-test, no grid widening.
- **v2/RP fixed-mix ensemble** (E13, s8): 30/70-70/30 all fail diff-CI; best
  terminal $4,174 < SPY. Mixture weights exhausted — do not re-tune.
- **True Antonacci GEM with international equity** (E9, s7): SPY/EFA/EEM rotation,
  AGG harbor. Mean WF Sharpe 0.435, DD -32.5%, DSR 0.301. FAIL. International
  rotation hurts badly in the 2010-2019 US equity bull market (fold-2 Sharpe 0.152).
  Country rotation CLOSED — do not retry with different harbors. The mechanism itself
  (country rotation) is the failure, not the harbor.
- **True Faber GTAA-5** (E10, s7, SPY/EFA/IEF/VNQ/DBC): DSR 0.766, CI misses.
  NOT closed — added to watch-list. Revisit in 3-5 years when DBC history is longer.
- **Sector momentum + SMA200 trend gate** (E11, s7): DD still -47.4% — gate
  did NOT fix the concentration problem. Sector rotation family CLOSED PERMANENTLY.
- Dual Momentum with SHY harbor (E7, s6): mean WF Sharpe 0.539, DD -36.7%.
  The SPY/QQQ/DIA rotation whipsaws regardless of harbor. Family closed.
- Kill-switch on v2 at ANY setting — tight -12/-15 (E4) and loose -20/-10
  (E8, s6) both failed: no DD improvement, Sharpe cost. Closed permanently.
- Faber GTAA-4 as a STANDALONE champion (E6, s6): fails significance vs SPY
  (DSR 0.897). NOT closed as an ensemble component — see watch-list.
- Raw daily SMA crossover (band=0); 50d SMA windows (noise).
- Vol targets ≤0.12 on trend-gated SPY (over-delever; Sharpe 0.69-0.76).
- Wider vol targets 0.21-0.30: flat surface, no gain over v2 (E1, 2026-07-14).
- Spot-VIX percentile de-risking overlays on v2, scale {0.5, 0}, pct {70,80,90}:
  failed DD/DSR/CI bars (E2, 2026-07-14). High VIX precedes high returns.
- Dual Momentum (Antonacci GEM) with TLT as defensive harbor: failed all bars
  (E3, s5). TLT harbor catastrophic in 2022 rising-rate regime.
- Cross-sectional sector momentum (top-N XL*, lookback 12-1mo): failed (E5, s5).
  Retry with trend gate also failed (E11, s7). Sector family permanently closed.
