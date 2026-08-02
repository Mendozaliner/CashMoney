# ROADMAP (reprioritized 2026-07-15 s7)

0. ~~Universe expansion~~ DONE s7: EFA, EEM, AGG, DBC, VNQ tested.
   ~~TRUE Antonacci GEM~~ DONE (E9, DISCARDED). ~~TRUE Faber GTAA-5~~ DONE (E10,
   DISCARDED on significance — added to watch-list for revisit when DBC has more history).
   ~~GTAA-5 revisit (DBC 19+ years)~~ DONE s24 (E36, DISCARDED — mean_wf 0.776,
   DSR 0.813, corr_v2 0.741; international+commodity equal-weight drag persists
   in 2010-2019 US bull). ~~Swensen 4-Asset Allocation~~ DONE s24 (E37, DISCARDED —
   mean_wf 0.748, DSR 0.923, DD -11.0% best-ever multi-asset, corr_v2 0.504).

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

6a. ~~E31 — CAPE value tilt on v2~~ DONE s22 (DISCARDED — CI straddles zero, corr_v2=1.000
   in OOS because CAPE above 90th pct throughout 2020-2025H). Notable: ALL 6 configs beat
   v2's mean WF Sharpe (best 0.937 vs 0.851) and best DD improved to -13.7% — the best
   ever for a single-equity strategy. CAPE concept NOT closed: valid at DECADE horizons;
   grid exhausted for this formulation; revisit with longer data or different mechanism
   (fractional Kelly under high CAPE). 6 configs burned (206 total after E31).

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

14. **Guardrails at every mark** (NEW s10, standing): run `backtest.guardrails.run_all()`
    at each session's portfolio mark; report any non-GREEN check in the daily briefing.
    Charter queue item "lessons from famous failures -> risk-limit guardrails" DONE s10
    (engineering, zero configs).

15. ~~Mean reversion (RSI-2, Bollinger, IBS)~~ DONE s11 (E17/E18/E19, all
    DISCARDED; E18 Bollinger watch-listed corr 0.364; RSI-2 + IBS families
    CLOSED). CHARTER RESEARCH QUEUE NOW FULLY EXPLORED (9/9).

16. ~~Multi-Asset CTA Trend~~ DONE s12 (E20, DISCARDED on CI — BUT NEW RECORDS:
    mean WF Sharpe 1.099, worst DD -6.19%, DSR 0.979; WATCH-LISTED for capital-
    preservation mandates; corr 0.635 above ensemble threshold). SPY/IEF/GLD is the
    superior universe (vs SPY/TLT/GLD — IEF less volatile in 2022 rate spike).
17. ~~Seasonal/Halloween Effect~~ DONE s12 (E21, DISCARDED and CLOSED: DSR 0.9267 <
    0.95; corr_v2 0.917 near-duplicate of v2; SMA200 gate already handles seasonal
    timing). Do NOT retry calendar-based overlays.

18. ~~v2+CTA Ensemble (corr threshold relaxed to 0.70)~~ DONE s13 (E22, DISCARDED —
    CI [−0.493,+1.225] straddles zero; OOS corr v2=0.943 far above threshold; best
    fold-1 Sharpe 1.170 and worst DD −6% show real bear-regime benefit but it's
    invisible in OOS bull-period CI). THRESHOLD ITEM CLOSED: further ensemble corr
    relaxation not productive without significance on the base strategies.
19. ~~Market Breadth Trend~~ DONE s13 (E23, DISCARDED and CLOSED — DSR 0.480 < 0.95;
    OOS corr v2=0.901 — sector breadth above SMA200 IS the same signal as SPY above
    SMA200 dressed up. No information added. Family permanently closed.)
20. ~~Low-Vol Sector Rotation~~ DONE s13 (E24, DISCARDED and CLOSED — DSR 0.464 < 0.95;
    fold-1 DD −37-48% — low-vol anomaly requires 500+ individual stocks, not 9 sector
    ETFs. Baker-Haugen effect is not observable at sector granularity. Family closed.)

21. **Session-completeness guard** (NEW s14, standing): at every sync, verify the
    PRIOR session's report file exists in reports/; if missing, reconstruct it from
    the session log before new work. Write the current report BEFORE pushing.

22. ~~Vigilant Asset Allocation (VAA)~~ DONE s15 (E25, 6 cfg, DISCARDED and CLOSED).
    Best VAA(n3,bp0.50): mean WF 0.626 < 0.844 bar, worst DD −41.85% >> −20.5%.
    DSR 0.9639 passes but fails all other gates. Root cause: breadth signal too coarse
    at n=3 assets (Keller paper used 12+). n=4 with EFA worse (reproduces E9 GEM
    international drag). VAA family PERMANENTLY CLOSED (180 configs total).

23. ~~Phase-3 stress-test harness~~ DONE s17 (engineering, zero configs):
    backtest/stress.py — bear-regime replay, 2x-cost runner, ±25% perturbation
    grid, collapse verdict; 8 tests, synthetic data only. STANDING RULE: do NOT
    run the harness on champion returns until a Phase-3 graduation candidate is
    declared (leakage guard).

24. ~~Donchian Channel / Turtle Trading~~ DONE s18 (E26, 4 cfg, DISCARDED and CLOSED).
    Best DCH(S1,tv0.15): mean WF 0.475 <0.844 bar, DSR 0.9531 (passes!), CI straddles
    zero, fold-1 Sharpe −0.158. Root cause: breakout entry on single-asset SPY without
    SMA200 anchor buys bubble tops (dot-com). Family PERMANENTLY CLOSED.

25. ~~52-Week High Proximity (George & Hwang 2004)~~ DONE s18 (E27, 4 cfg, DISCARDED
    and CLOSED). Best 52wk(H0.95,L0.85): mean WF 0.634, DSR 0.9452 (<0.95), corr_v2
    0.937 (near-duplicate). CRITICAL FINDING: 52-week high anchoring IS the SMA200
    signal on a broad market index — both encode "market near recent peak." No new
    information. Family PERMANENTLY CLOSED.

26. ~~ADX Trend Strength (Wilder 1978)~~ DONE s18 (E28, 4 cfg, DISCARDED). Best
    ADX(p14,t20): mean WF 0.797, DD −18.45%, DSR 0.856 (<0.95), corr_v2 0.804. Notable:
    ADX(p14,t25) produced DD −9.65% (2nd-best ever) and OOS Sharpe 1.003, but fold-2
    collapses (bull-market ADX instability). Not watch-listed (DSR <0.95, corr >0.50).
    NOT permanently closed — ADX overlay may revisit in Phase 3 capital-preservation work.

27. ~~Live-track checkpoint tooling~~ DONE s19 (engineering, zero configs):
    backtest/live_track.py — monthly live-vs-SPY checkpoints, consecutive-beat
    counter, live worst-DD, PSR MinTRL. STANDING: summary() at every mark; the
    July completed-month checkpoint prints in the first August session.

28. ~~VIX-Regime Dynamic Ensemble~~ DONE s20 (E29, 4 cfg, DISCARDED and CLOSED).
    Best RE(v25/c40,60/40): mean WF 0.825, DD −20.73%, DSR 0.9715 (✓), CI
    [−0.589,+0.927] straddles zero, corr_v2=0.967 — highest correlation ever.
    Root cause: crisis periods (VIX>30) are rare (~10% of days); CTA-SPY sleeve
    replicates the SMA200 gate — VIX regime switching IS v2 in macro clothing.
    Family PERMANENTLY CLOSED (corr 0.967 >> 0.70 ensemble threshold; CI fails).

29. ~~Inter-Market Bond-Equity Relative Strength~~ DONE s20 (E30, 4 cfg, DISCARDED
    and CLOSED). Best IM(lb63,scale0.50): mean WF 0.769, DD −20.37%, DSR 0.9468
    (<0.95), CI [−0.674,+0.824] straddles zero, corr_v2=0.974. Root cause: when IEF
    outperforms SPY over 3 months, v2's SMA200 gate has already signaled cash —
    the inter-market filter adds caution after v2 already knows. Murphy (1991)
    bond-leading-equity relationship works at the stock level, not at the broad index
    level where SMA200 captures the same information. Family PERMANENTLY CLOSED.

30. ~~CAPE Value Tilt (E31)~~ DONE s22 (DISCARDED — CI straddles zero; corr_v2=1.000 OOS).
    See 6a above. 6 configs. CAPE family NOT permanently closed.

31. ~~Yield Curve Regime Overlay (E32)~~ DONE s22 (DISCARDED and PERMANENTLY CLOSED —
    corr_v2=0.990; 2022-2024 inversion + bull market severely hurt OOS). Best YC(lb63,s0.75):
    mean_wf=0.865, DD=-19.95%, DSR=0.976, CI=[-0.554,+0.899]. Root cause: yield curve at
    ETF relative-momentum level (IEF vs SHY) is structurally absorbed by v2's SMA200 gate
    (both respond to the same macro cycle, SMA200 gate faster at turning points). The signal
    operates at 4-8 quarter business-cycle frequency, not daily-return frequency. Do NOT
    re-test yield-curve slope signals on ETF relative momentum — they will always be
    dominated by v2 in the OOS equity bull markets. 6 configs.

32. **Tactical Bond Cash Sleeve (E33)** — DISCARDED (CI straddles zero) but NOT closed.
    Best TB(w200,f1.0): mean_wf=0.882, DD=-20.17%, end1k=$10,467 (+$2,085, +25% vs v2).
    corr_v2=0.975. Economic significance is real: in equity bear markets (v2 in cash),
    Treasury rally + IEF SMA200 gate compounds the outperformance. Statistical significance
    cannot be demonstrated in the current 5-year OOS window. Revisit: (a) after 12+ live
    months extend the effective OOS window; (b) as a capital-preservation portfolio product.
    Do NOT revisit as a Phase-2 growth-mandate champion change.

33. **Defensive Dual-Asset Cash Sleeve (E34, s23)** — DISCARDED (CI straddles zero). NOT closed.
    Best DDAS(g0.25,w200): mean_wf=0.887, DD=−19.76%, end1k=$10,565, DSR=0.978, corr_v2=0.972.
    Split defensive cash between IEF (75%) and GLD (25%), each SMA200-gated independently.
    end1k=$10,565 beats E33 ($10,467) and v2 ($8,382). Key finding: gld_frac=0.25 (25% gold)
    improves over pure IEF in all 3 folds; gld_frac=1.0 fails DD bar (−22-29%). Concept of
    adding gold to defensive sleeve is sound but CI requires more bear-market data. Revisit
    alongside #32 after 12+ live months. Grid exhausted (8 configs burned; no re-testing).

34. **Correlation-Regime Defensive Switch (E35, s23)** — DISCARDED (CI straddles zero). NOT closed.
    Best CRDS(lb63,t0.00): mean_wf=0.920, DD=−20.17%, end1k=$11,420 (NEW ALL-TIME RECORD),
    DSR=0.988, corr_v2=0.965. Uses rolling 63-day corr(SPY_ret, IEF_ret) to dynamically
    select IEF (normal/deflation regime, corr<threshold) or GLD (inflation regime, corr≥threshold)
    as the defensive cash-sleeve asset. ALL 9 configs beat v2 mean_wf (0.897-0.920) and
    all produce end1k > $10,962. The stock-bond correlation is a genuine macro-regime signal
    (academic: Ilmanen 2011, Asness 2012, Campbell 2020). Critically surpasses E33 (+$953)
    and v2 (+$3,038). Cannot achieve statistical significance in 5-year OOS window — defensive
    improvements occur only during ~35% cash periods. Revisit after 12+ live months.
    Concept NOT permanently closed — strongest economic signal found for the cash sleeve.

35. ~~Inverse-Vol GTAA on Swensen-4 (E38, s25)~~ DONE. DISCARDED (CI straddles zero). NOT closed.
    Best IVG(vl60,sma150): mean_wf=0.968 (BEATS v2 0.851), DD=−8.87% (MUCH BETTER than v2),
    DSR=0.9565 (✓). CI=[−0.912,+1.066] straddles zero. corr_v2=0.539 (near ensemble threshold).
    end1k=$3,840 — 54% less than v2 due to diversification drag in sustained US equity bull.
    All 4 configs beat v2 mean_wf bar. Exceptional DD profile (all < −12%). The IVG concept IS
    an improvement over E37 equal-weight on DD (−8.87% vs −11.0%) as hypothesized.
    sma150 beats sma200 (more responsive); vol_lookback=60 beats 252 (less stale).
    corr_v2=0.539 is the closest to ensemble-eligible of any multi-asset strategy (threshold 0.50).
    Condition to revisit: if a bear market materializes making IEF/GLD/VNQ allocations valuable,
    or if 3-5 more live years push the CI lower bound > 0. Grid exhausted (4 configs).

36. ~~Real Earnings Growth Shiller Overlay (E39, s25)~~ DONE. DISCARDED (CI straddles zero). NOT closed.
    Best EG(thr-5%,sc0.75): mean_wf=0.857 (BEATS v2 bar), DD=−16.88%, DSR=0.9650 (✓).
    CI=[−0.611,+0.853] straddles zero. corr_v2=0.991 — near-duplicate of v2 (expected: it IS
    v2 with occasional de-risking). end1k=$7,533 (close to v2 $8,382 but lower).
    The real earnings growth signal DOES vary meaningfully in the OOS window — distinguishing it
    from E31 CAPE (which was static high-decile OOS). H2-2022 contraction correctly de-risked;
    2023-24 recovery correctly un-risked. But de-risking occurs only ~15-20% of days, providing
    insufficient OOS draws to clear the CI. EG(thr-10%,sc0.75) best OOS Sharpe 0.855.
    Condition to revisit: after a genuine earnings recession (2001/2008 scale) extends the live
    sample. The Shiller feed is correctly plumbed and no-lookahead enforced — mechanism is sound.
    Grid exhausted (4 configs). Do NOT re-tune thresholds.

37. ~~Minimum Variance Portfolio (E41, s27)~~ DONE. DISCARDED (CI straddles zero). NOT closed.
    Best MV(lb60,gate=F): mean_wf=0.887 (BEATS v2 bar 0.851), DD=−20.1%, DSR=1.000
    (within-session). CI=[−0.049,+0.844] straddles zero. corr_v2=0.267 — NEW ALL-TIME
    PROJECT RECORD for lowest correlation to v2 (prior record: Bollinger E18 at 0.364).
    Ensemble-eligible (well below 0.50 threshold). end1k=$3,251 vs v2=$9,199 — huge raw
    return deficit driven by 62% average IEF allocation.
    Philosophy: Markowitz (1952) modern portfolio theory — analytical minimum variance weights
    from rolling 60 or 120-day covariance matrix. First experiment in this project to use the
    full Σ matrix. The unconstrained solution (clipped long-only) concentrates heavily in IEF
    because IEF has far lower variance and negative/zero correlation with SPY in crisis.
    Root cause of failure: 62% IEF weight costs ~3-4% CAGR in the 2000-2026 bull-market era.
    Fold-1 IS Sharpe was 0.96 (dot-com/GFC era) — the strategy's genuine value shows in bearish
    environments. Fold-3 OOS 2020-2025 Sharpe = 0.327 — catastrophic in equity bull market.
    Condition to revisit: (a) a sustained bear market (2008-style) materialises — MinVar's IEF
    allocation would compound the defensive benefit dramatically; (b) v2 achieves Criterion-1
    significance AND CI improves — then a v2+MinVar ensemble with corr=0.267 is compelling.
    Grid exhausted (4 configs: lb60/lb120 × gate=T/F). Do NOT re-tune without new regime data.

## Priority order for next sessions (updated s27)
1. (#9) Live-track marks — highest priority for Phase-2 graduation.
   First full-month checkpoint ~2026-08-13. Portfolio $996.15, tracking SPY 1:1.
2. (#10) Monthly v2 full-sample significance re-check — CI now [−0.0274,+0.6778]
   (improved +0.0015 from s26 [−0.0289,+0.6834]). Re-check in first September session.
3. (#14) Guardrails run at every mark — standing. ALL GREEN in s27.
4. **MinVar ensemble investigation (NEW s27):** E41 corr_v2=0.267 is the lowest
   correlation ever found. A v2+MinVar ensemble is theoretically compelling (genuinely
   different signals). Pre-condition: v2 must achieve Criterion-1 significance first.
   Revisit also if a bear market materialises (E41 fold-1 Sharpe was 0.96).
5. Phase-2 graduation review — first checkpoint ~2026-08-13; needs 3 consecutive months.
6. (#33, #34, #35) Defensive cash sleeve family revisit after 12+ live months: CRDS (E35,
   $11,420) and DDAS (E34, $10,565) as capital-preservation product consideration.
   CRDS is the priority given its record-setting terminal value and consistent all-config
   outperformance. Do NOT change the current growth-mandate champion.
7. Fractional Kelly position sizing on v2 (Phase-3 material, after Criterion-1 significance).
   Infrastructure now in place: tools/kelly.py. v2 full-Kelly = 7.76x; vol-target implies
   ~0.22 Kelly at target vol. Phase-3 experiment: run Sharpe-estimated Kelly directly.
8. IVG corr_v2=0.539 is close to ensemble-eligible (threshold 0.50) — revisit as ensemble
   component IF a bear market makes the diversification benefit economically significant.

## Research scope update (s27)
261 configs burned. 16 families permanently closed: sector, kill-switch, blended-mom,
AAA, RSI-2, IBS, seasonal, market-breadth, low-vol-sector, country-rotation,
VAA/breadth-protection, Donchian/turtle, 52wk-high, VIX-regime-ensemble,
inter-market-bond-equity, yield-curve-ETF-relative-momentum.
Open families: CAPE (decade-horizon formulation), Tactical Bond (capital-preservation,
E33/E34/E35 cluster), Correlation-Regime (capital-preservation), Fractional Kelly (Phase-3),
GTAA/Swensen/IVG (revisit with dynamic/inverse-vol weights if bear market materializes),
Earnings Growth Shiller overlay (revisit after genuine earnings recession on live data),
MinVar ensemble (NEW — corr_v2 0.267 record low; revisit when v2 achieves significance
or bear market materialises).
Grid exhausted on: E33-E35 defensive sleeve variants (cannot re-test without new data).
Grid exhausted on: E36 GTAA-5; E37 Swensen-4; E38 IVG (4 configs); E39 Earnings Growth;
E41 MinVar (4 configs, cov_lookback/sma_gate space covered).

## Negative results (do NOT re-test in the original form)
- **Faber GTAA-5 (equal-weight 5-asset, SMA-gated)** (E36, s24, SPY/EFA/DBC/VNQ/IEF):
  best GTAA5(w252,b0.03) mean_wf=0.776 (< 0.844 bar), DD=−13.6%, DSR=0.813 (< 0.95).
  CI straddles zero; corr_v2=0.741 (above watch-list threshold). Terminal $3,546 vs v2
  $8,382 — 57% less wealth over 26 years. Root cause: equal-weight 20% to EFA and DBC
  drags severely in 2010-2019 US equity bull (fold-2 Sharpe 0.298-0.486). Hysteresis
  band (b0.03) consistently helps vs no band. NOT permanently closed — the diversification
  mechanism is valid; the equal-weight constraint in a US-dominant equity era is the failure.
  Do NOT retry with the same equal-weight architecture without a dynamic allocation mechanism.
- **Real Earnings Growth Shiller Overlay (E39, s25, threshold/scale on v2)**: best EG(thr-5%,sc0.75)
  mean_wf=0.857 (> v2 bar), DD=−16.88%, DSR=0.9650 (✓). CI=[−0.611,+0.853] straddles zero.
  corr_v2=0.991 (near-duplicate — it IS v2 with occasional de-risking). end1k=$7,533 vs v2 $8,382.
  The signal correctly identifies 2022 earnings contraction and 2023-24 recovery but de-risking events
  are too infrequent (~15-20% of days) to clear the CI in the current sample window. The Shiller feed
  is correctly no-lookahead (1-month shift). Grid exhausted. Do NOT re-tune; revisit after earnings
  recession extends the live sample with new bear-market draws.
- **Inverse-Volatility GTAA on Swensen-4 (E38, s25, SPY/IEF/GLD/VNQ)**: best IVG(vl60,sma150)
  mean_wf=0.968 (> v2 0.851), DD=−8.87% (much better than v2 −20.5%), DSR=0.9565 (✓). All 4 configs
  beat v2 mean_wf bar (0.841-0.968). CI=[−0.912,+1.066] straddles zero; corr_v2=0.539 (near ensemble
  threshold of 0.50 — closest any multi-asset strategy has come). end1k=$3,840 vs v2 $8,382 — the IEF/
  GLD/VNQ budget (75%) drags terminal wealth in sustained US equity bull. The inverse-vol mechanism IS
  the right improvement over equal-weight E37 (DD improved from −11.0% to −8.87%), but bull-market
  returns dominate the 26-year sample, making the CI impossible to clear. Do NOT retry equal-weight
  or wider grids. Revisit as ensemble component if corr_v2 drops below 0.50 on extended data.
- **Swensen 4-Asset Allocation (equal-weight 25%, SMA-gated)** (E37, s24, SPY/IEF/GLD/VNQ or DBC):
  best SWN4(w150,DBC) mean_wf=0.748 (< 0.844), DD=−11.0% (lowest worst-DD ever for
  multi-asset), DSR=0.923 (< 0.95). CI straddles zero; corr_v2=0.504 (marginally above
  0.50 watch-list threshold). Terminal $3,002 vs v2 $8,382 — 64% less wealth. VNQ configs
  more consistent (fold-2 Sharpe 0.411-0.676) vs DBC (fold-2 0.124-0.515). Root cause:
  same equal-weight problem as E36; adding GLD (inflation hedge) and IEF (deflation hedge)
  at 25% each costs return during sustained bull markets. The DD improvement (−11%) is
  genuine but insufficient to compensate the Sharpe shortfall. NOT permanently closed —
  inverse-vol weighting on the Swensen universe (similar to E12 risk parity) might
  preserve the DD benefit; do NOT retry with pure equal-weight.
- **Inter-Market Bond-Equity Relative Strength, IM(lb21-126, scale0.0-0.5)** (E30, s20):
  best IM(lb63, scale0.50) mean WF 0.769 (< 0.844 bar), DD −20.37%, DSR 0.947 (< 0.95),
  CI straddles zero, corr_v2 0.974. When IEF outperforms SPY over any multi-month lookback,
  SPY has already been declining and v2's SMA200 gate has already flagged risk-off — the
  filter is structurally redundant. Scale=0.0 (full exit in risk-off) makes it worse:
  mean_wf 0.601, DD −24.42%. Murphy (1991) bond-leading-equity applies at individual
  security level, not at the broad-index level. Do NOT re-test bond-equity relative
  momentum overlays on single broad indices — the information is already in SMA200.

- **VIX-Regime Dynamic Ensemble (VIX<20/20-30/>30 thresholds)** (E29, s20):
  best RE(v25/c40, 60/40 blend) mean WF 0.825 (< 0.844 bar), DD −20.73%, DSR 0.972 (✓),
  CI [−0.589,+0.927] straddles zero, corr_v2 0.967 — highest OOS correlation ever recorded.
  Tried wider thresholds (v25/c40) and v2-only crisis mode: all configs ≥ 0.814 correlation.
  Crisis periods (VIX>30) are ~10% of days; CTA-SPY sleeve (the crisis alpha source) uses
  the same SMA200 gate as v2 during non-crisis periods, creating structural redundancy.
  Do NOT re-test VIX-triggered ensemble switching on SPY — regime detection is already
  implicit in v2's price-based trend gate, and multi-asset CTA correlation to v2 is too
  high (E20: 0.635; E22: 0.943; E29: 0.967) for any ensemble benefit.

- **ADX Trend Strength Filter, ADX(p14-20, t20-25) on SPY** (E28, s18): best ADX(p14,t20)
  mean WF 0.797 (< 0.844 bar), DD −18.45% (better than v2), DSR 0.856 (fails 0.95). CI
  straddles zero; corr_v2 0.804 (above watch-list threshold). Grid burned — do NOT
  re-tune period or threshold. Notable: ADX(p14,t25) DD only −9.65% (second-best ever)
  and OOS Sharpe 1.003, but fold-2 Sharpe 0.463 reveals bull-market instability. The ADX
  concept is not closed — it may revisit as a Phase-3 capital-preservation overlay, but
  not as a standalone growth-mandate strategy.
- **52-Week High Proximity Momentum** (E27, s18, George & Hwang 2004): best
  52wk(H0.95,L0.85) mean WF 0.634, DD −19.75% (marginally better than v2), DSR 0.9452
  (fails 0.95 bar), CI straddles zero, corr_v2 0.937. Root cause: on a broad market
  index, proximity to 52-week high and proximity to SMA200 encode nearly identical
  information. Individual-stock behavioral anchoring does not aggregate to index level.
  Do NOT re-test anchor-based signals on single broad indices — they are v2 in disguise.
- **Donchian Channel Breakout / Turtle Trading (20-day entry, 10-55 day exit)** (E26, s18,
  Dennis & Eckhardt 1983): best DCH(S1,tv0.15) mean WF 0.475 (< 0.844 bar), DD −21.4%,
  DSR 0.9531 (passes!), CI straddles zero, corr_v2 0.610. Fold-1 Sharpe −0.158 —
  breakout on single-asset SPY enters on new highs (tech bubble top in 2000) without the
  SMA200 level anchor to stay out. Terminal value $2,105 vs v2 $8,381 (75% less wealth).
  Do NOT retry channel-breakout without a separate trend gate; the SMA200 gate IS the
  necessary stabilizer that Donchian lacks.
- **Vigilant Asset Allocation VAA(n3,bp0.50)** (E25, s15): DSR 0.9639 passes; best
  mean WF Sharpe 0.626 (< 0.844 bar), worst DD −41.85%, diff-CI [−0.653,+1.144]
  straddles zero, corr_v2 0.60 > 0.50 threshold. Terminal $9,202 > v2 $8,382 on raw
  return (driven by fold-3) but fold-2 (2010-2019) Sharpe 0.409 shows the breadth
  signal collapses in bull markets with only 3 offensive assets. n=4 (EFA) even worse —
  reproduces GEM's international drag. Family permanently closed.
- **v2+CTA Ensemble (50/50, 60/40, 40/60)** (E22, s13): DSR 0.981 passes; best DD −10.8%
  and mean WF Sharpe 1.048. FAILED CI [−0.493,+1.225] and OOS corr to v2=0.943 (far
  exceeds threshold). Bear-regime benefit is real (fold-1 Sharpe 1.170 vs v2 0.859) but
  the bull-era CI cannot clear zero. Do NOT re-test with adjusted weights — 3 alphas burned.
  Capital-preservation note: the Ensemble's risk profile (DD −10.8%, Sharpe 1.048) IS
  superior to v2 for non-growth mandates; consider as a separate portfolio product.
- **Market Breadth Trend on SPY** (E23, s13): sector SMA200 breadth is 0.901 correlated
  to v2 OOS. This IS the same signal. Family permanently closed.
- **Low-Vol Sector Rotation (9 SPDR sectors, monthly)** (E24, s13): fold-1 DD −37-48%;
  low-vol anomaly not observable at sector-ETF granularity. Family permanently closed.
- **Connors RSI-2 on SPY, SMA200-gated** (E17, s11): best e5/x80 mean WF 0.756,
  DD -7.9%, DSR 0.485, CI [-1.27,+0.85]. Strong 2000s fold then monotone decay —
  the published-edge-decay pattern. Family CLOSED.
- **Bollinger(20,k) lower-band MR on SPY** (E18, s11): best k2.5/upper_half mean
  WF 0.896 (> v2), DD -8.4%, corr to v2 0.364 (lowest ever) but DSR 0.848 and CI
  straddle. NOT closed — WATCH-LISTED as ensemble diversifier; grid burned.
- **Pagonidis IBS on SPY, SMA200-gated** (E19, s11): best e0.1/x0.8 mean WF 0.244,
  DD -22.8%, DSR 0.616. EOD next-close fills give away the overnight edge; costs
  eat the rest. Family CLOSED permanently.
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
