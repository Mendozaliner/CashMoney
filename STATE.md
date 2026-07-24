Updated: 2026-07-24 s20 (E29 VIX-Regime Ensemble DISCARDED&CLOSED, E30 Inter-Market Bond-Equity Filter DISCARDED&CLOSED. 8 new configs (200 total). E29: mean WF 0.825, DSR 0.9715, CI [−0.589,+0.927] straddles zero, corr_v2=0.967 — VIX regime switching duplicates v2; crisis periods ~10% of days; CTA-SPY replicates SMA200 gate. E30: mean WF 0.769, DSR 0.9468 (<0.95), CI [−0.674,+0.824] straddles zero, corr_v2=0.974 — bond-equity relative momentum adds nothing when v2's trend gate already detects risk-off. Both families PERMANENTLY CLOSED. New mark $984.35 (SPY 738.18, −1.235% day, −1.565% all-time; SPY since live −1.467%). Exposure 1.0; no trades. Guardrails ALL GREEN. Suite 101/101 (87 prior + 14 new). v2 $8,381/$1k since 2000.)
Updated: 2026-07-23 s19 (second run today; zero-config engineering. backtest/live_track.py shipped: monthly live-vs-SPY graduation checkpoints, consecutive-beat counter, live worst-DD, PSR-based MinTRL (Bailey & LdP 2012). Suite 87/87. First real-track run: 0 completed months, worst live DD -1.69%, MinTRL infinite while v2 fully invested (no live edge accrues at exposure 1.0 - documented in research/2026-07-23-s19-live-track-checkpoints.md). Mark CARRIED $996.65 (2026-07-22 close; no new completed close). Exposure 1.0; no trades. Guardrails ALL GREEN. Configs unchanged 192. STANDING: run live_track.summary() at every mark; July checkpoint prints in first August session.)
Updated: 2026-07-23 s18 (E26 Donchian/Turtle DISCARDED&CLOSED, E27 52wk-High DISCARDED&CLOSED, E28 ADX Trend Strength DISCARDED. 12 new configs (192 total). Best: ADX(p14,t25) DD −9.65% (2nd-best ever), OOS Sharpe 1.003 — but DSR 0.856 <0.95 bar and fold-2 Sharpe 0.463. 52wk-High (George&Hwang 2004) corr_v2=0.937 — near-duplicate of v2. New mark $996.65 (2026-07-22 close, −0.116% day, −0.335% all-time). Exposure 1.0; no trades. Guardrails ALL GREEN. Suite 79/79. v2 CI re-check: [−0.0128,+0.7077] straddles zero.)
Updated: 2026-07-22 s17 (Engineering run, zero configs — Phase-3 stress harness built: backtest/stress.py (regime replay, 2x-cost runner, ±25% perturbation grid, collapse verdict) + 8 synthetic-only tests; suite 63/63. New mark $997.81 (2026-07-21 close, +0.834% day, −0.219% all-time). Exposure 1.0; no trades. Guardrails ALL GREEN. Configs unchanged 180.)
Updated: 2026-07-21 s16 (Zero-config maintenance/analysis run — queue exhausted. M3 exposure-profile memo on frozen v2: since 2000 fully invested 64.6% of days, cash 26.9%, avg exposure 0.716; sat out dot-com −29.8% and GFC −31.8%, cost ~8 whipsaws of +5–12%. Mark carried $989.56 (2026-07-20 close). Guardrails ALL GREEN. 55/55 tests. Configs unchanged 180.)
Updated: 2026-07-21 s15 (E25 VAA Vigilant Asset Allocation — DISCARDED and CLOSED. Best VAA(n3,bp0.50) mean WF 0.626 < 0.844 bar, worst DD −41.85% >> −20.5% bar, DSR 0.9639 (✓), corr 0.60 > 0.50 threshold. Not watch-list eligible. VAA family CLOSED — breadth signal too coarse at n=3 assets. Mark $989.56 (2026-07-20 close). Guardrails G1–G7 ALL GREEN. 55/55 tests. Configs 174→180.)# STATE — CashMoney research system

Updated: 2026-07-20 s13 (E22 Ensemble v2+CTA, E23 Market Breadth, E24 Low-Vol Sector Rotation — all 3 DISCARDED. CI straddles zero on all (24th consecutive failure). Best: E22 Ensemble mean WF Sharpe 1.048, worst DD −10.8%, DSR 0.981 — but CI [−0.493,+1.225] fails and OOS corr to v2 jumped to 0.943. Configs 174. Mark carried $991.16 [data 1 trading day stale]. Guardrails ALL GREEN. 49/49 tests.)

## PHASE 2 — PROVE (entered 2026-07-14)
Champion **v2 is FROZEN** as the live exam strategy. The live-outperformance
clock starts **2026-07-14** (first fresh mark once the data Action has run;
3 consecutive months of beating SPY, MaxDD < 20%, is the Phase-2 bar).
All new research runs in SEPARATE SLEEVES and must NOT touch the frozen live
track. Champion changes are allowed only if v2 decisively fails (trails SPY by
>5% over 6+ weeks live). See SKILL.md for keep/revert + significance gates.

## Graduation tracker (updated 2026-07-15 s8)
1. Beats S&P risk-adjusted OOS: POINT-PASS / SIGNIFICANCE-FAIL — full-sample
   diff CI [-0.009,+0.708] — misses clearing zero by 0.009. Not passed.
   GTAA ensemble blocked (corr 0.721). NEW s8: RP sleeve corr 0.467 (< 0.50
   threshold) and passes DSR (0.982), but v2/RP ensemble (E13) still fails the
   diff-vs-SPY CI ([-0.269,+1.364]) and lags SPY on raw terminal value
   ($4,174-$6,297 vs $6,768 per $1k since 2000). Not passed.
2. Live 3-mo outperformance: clock running (0/3 months). Day 2 mark carried
   in s8 (no new close intraday); $1,002.55, tracking SPY 1:1 fully invested.
3. MaxDD < 20%: live +0.355% since inception; worst backtest fold -20.5%.
4. Full costs (0.15%/trade): PASS — negligible drag at ~2 trades/yr.
Phase-transition: not met (needs 3 live months + significance on #1).

## Live track baseline (migration 2026-07-14)
Portfolio re-based from SPY_PROXY (stale, ended 2025-12-19) to real SPY cache:
$999.00 carried, 1.333476 SPY units @ 749.17 (2026-07-13 close). Live clock and
all live-vs-SPY comparisons measure from this mark. Costs standard now 0.15%.
**Latest mark (2026-07-22 close, session 18):**
1.333476 SPY × $747.41 = **$996.65** (−0.116% day, −0.335% all-time from $1,000
inception). SPY since live baseline: −0.235%. Portfolio tracking SPY 1:1 fully invested.
v2 exposure confirmed 1.0 (747.41 > SMA200+3% band 715.53; 20d vol 10.7% < 18%). No trades.
Guardrails G1–G7 ALL GREEN. Peak $1,006.52, current drawdown from peak −0.98% (GREEN).

## Standing briefing instructions (per Mr. Menéndez, 2026-07-14)
- FORMAT (added later on 2026-07-14, SUPERSEDES the long template): the daily
  email must be a TWO-MINUTE READ MAX (~250-350 words + two small tables).
  Structure: (1) SCOREBOARD table — live value, day change, vs SPY day/since
  inception, worst dip, holdings one line; (2) TRACK RECORD table — $1k
  backtest from 2000/2010/2020 → strategy vs SPY (and vs EWC/ACWI once
  cached): final $, %/yr, worst loss ONLY; (3) RESEARCH — one line per
  experiment: name, verdict, ≤10-word reason; plus one line for anything
  added/removed (data, tools); (4) STATUS — the 4 graduation checks as a
  single ✓/✗ line each + live-clock months; (5) news digest max 2 sentences;
  (6) short sign-off + logo. No long prose sections. Charts only when
  something changed.
- BENCHMARK PANEL: once the expanded cache lands, every session's report and
  briefing scoreboard must compare the champion/live track not only to SPY/
  QQQ/DIA/Mag-7 but also to the Canadian market (EWC total-return proxy;
  ^GSPTSE price index) and major international indexes (^FTSE, ^N225,
  ^GDAXI, ^HSI, ACWI). Note plainly which markets beat the strategy over the
  comparison window. Price indexes exclude dividends — say so when citing them.
- MARKET CONTEXT in every daily briefing must include a short CROSS-SOURCE NEWS
  DIGEST compiled autonomously via web search: start from wire services
  (Reuters, AP) for the factual baseline, then check outlets across the
  spectrum (e.g. WSJ, FT, Bloomberg, plus at least one left- and one
  right-leaning mainstream outlet). Where coverage disagrees, REPORT the
  disagreement rather than averaging it away. Name the sources used each day.
- The digest is briefing color ONLY. It must never feed the trading model or
  influence rebalancing — strategy inputs remain prices/vol/T-bill yield.
- Performance-review charts (assets/charts/) may be refreshed and embedded in
  briefings via raw.githubusercontent URLs when relevant.

## Environment constraints
- Research sandbox: only github.com reachable; all market-data APIs blocked.
  This is why data now arrives via git, not direct fetch.
- PRIMARY DATA (new 2026-07-14): daily OHLCV for the full universe, 2000-01-01
  → present, in `data/cache/ohlcv/` — refreshed EVERY WEEKDAY by a GitHub
  Action (`.github/workflows/update-data.yml` → `scripts/fetch_data.py`) that
  runs on GitHub's servers (full internet). Read via `data.loader.load_ohlcv()`
  / `load_universe()`; check `data.loader.data_freshness()` each session.
  Coverage confirmed 28/28 tickers on first run.
- Universe now AVAILABLE (was blocked): SPY DIA QQQ IWM; XLK XLF XLE XLV XLY
  XLP XLI XLU XLB XLRE XLC; TLT IEF SHY GLD; AAPL MSFT GOOGL AMZN NVDA META
  TSLA; ^VIX; ^IRX. Multi-asset strategies (dual/cross-sectional momentum,
  rotation) are no longer blocked.
- Deep-history SPY total-return proxy (1885→, `load_spy_proxy()`) retained for
  long-horizon robustness checks only. VIX snapshot retained.

## Operational guardrails (new 2026-07-16 s10)
- `backtest/guardrails.py` — 7 reporting-only guardrails codified from famous
  failures (LTCM, Niederhoffer, Quant Quake, Amaranth; see
  research/2026-07-16-s10-famous-failures-guardrails.md): G1 leverage cap 1.0,
  G2 instrument whitelist (no derivatives/short-vol), G3 no revenge sizing,
  G4 concentration caps (stock 20%/sector 30%, broad index exempt), G5 vol-spike
  monitor (2x 1y-median or 4-sigma day -> AMBER), G6 drawdown ladder
  -10/-15/-20% AMBER/RED/BREACH (reporting only, never auto-liquidation, per
  E4/E8 evidence), G7 stale-data guard (>4d: no live marks/rebalance).
  12 tests in tests/test_guardrails.py. STANDING ITEM: run `run_all()` at every
  session mark; any non-GREEN goes in the briefing.

## Statistical-honesty tooling (new 2026-07-14)
- `backtest/evaluation.py` — deflated Sharpe ratio (penalizes # of trials),
  bootstrap CIs on a metric and on strategy-minus-SPY difference, after-tax and
  do-nothing comparisons. 8/8 tests in `tests/test_evaluation.py`.
- `research/preregister.py` — pre-registration log + hard cap of
  MAX_CONFIGS_PER_IDEA=12; records to `research/hypotheses.jsonl`.
- Keep/revert now requires: pre-registered hypothesis, deflated Sharpe >= 0.95,
  AND a bootstrap difference-vs-SPY CI that clears zero. No crowning on noise.

## Champion (v2, adopted session 2)
**vol_target(target_vol=0.18, lookback=20)** — exposure = SMA200/3%-band trend
gate × min(1, 0.18 / realized_vol_20d), cap 1.0, T-bill yield on cash sleeve,
0.1% costs on traded notional. Engine: backtest/vector_engine.py (fractional;
cross-validated vs backtesting.py).
Prior champion v1: sma_trend(200, 0.03), cash at 0%.

## Baselines & champion metrics — REAL DATA (2026-07-14 s4, 0.15% costs, WF folds 2000-09/2010-19/2020-2025H, 12-mo holdout locked)
| Config | Sharpe by fold | Worst DD |
|---|---|---|
| SPY B&H | 0.088 / 0.919 / 0.736 | -55.2% |
| QQQ B&H | -0.011 / 1.031 / 0.818 | -83.0% |
| Mag-7 eqw | 0.668 / 1.252 / 1.151 | -63.9% |
| v1 trend | 0.865 / 0.769 / 0.842 | -20.6% |
| v2 champion | 0.859 / 0.784 / 0.889 | -20.5% |
v2 mean WF Sharpe 0.844 (v1: 0.825). v2 DSR 0.966 vs 18 trials (s4); vs 32 trials (s5)
v2-minus-SPY CI [-0.56,+0.89] — not yet significant. After-tax do-nothing check 2020-2025H:
buy-and-hold won ($1.92 vs $1.56 per $1). **$1k test (2000→2026-07-14, real data s7):**
v2 $9,257.88 > QQQ $9,014.44 > SPY $8,249.83 > DIA $8,138.90 — v2 WINS on Sharpe AND
terminal value. Mag-7 eqw $83,104 (2012+ only, concentrated tech). Legacy PROXY-data table below kept for history.

## Baselines & champion metrics (LEGACY proxy data, vector engine, costs included)
| Config | Period | CAGR % | Sharpe | Sortino | MaxDD % | Turnover/yr | $1k → |
|---|---|---|---|---|---|---|---|
| SPY B&H | IS 2010-2019 | 13.22 | 0.920 | 1.151 | -19.35 | 0.1 | 3456 |
| v2 | IS 2010-2019 | 8.63 | 0.790 | 0.902 | -20.33 | 1.4 | 2286 |
| SPY B&H | OOS 2020 → 2025-12-19 | 15.00 | 0.778 | 0.956 | -33.72 | 0.2 | 2301 |
| v1 (prior) | OOS | 11.58 | 0.876 | 0.963 | -20.76 | 1.5 | 1922 |
| **v2** | OOS | 11.95 | **0.967** | 1.111 | **-17.90** | 2.1 | 1960 |

## Portfolio
portfolio.json created session 2 (session 1 omitted it): $1,000 inception
2026-07-13, fully invested per v2 (exposure 1.0), value $999.00 after entry cost.
**Current value: $997.81** (2026-07-21 close, session 17 mark). 1.333476 SPY units
@ $748.28. All-time: −$2.19 / −0.219% from $1,000 inception. No rebalance needed;
exposure 1.0 confirmed.

## Watch-list (not adopted; revisit under stated conditions)
- **CTA Multi-Asset Trend SPY/IEF/GLD (vt0.12)** (E20, s12): mean WF Sharpe **1.099**
  (NEW RECORD vs all 21 experiments), OOS Sharpe 1.112, worst DD **−6.19%** (NEW RECORD),
  DSR **0.979** (passes). Failed: diff-vs-SPY CI [−0.588,+1.302] straddles zero; corr_v2
  0.635 > 0.50 ensemble threshold. Terminal $1k from 2000: $3,754 vs v2 $8,382 (raw-return
  giveaway in bull markets, same flaw as RP/PP). Condition to revisit: as ALTERNATIVE
  CHAMPION for capital-preservation mandates or risk-reduction sleeves; OR if live data
  extends the CI lower bound > 0. Also revisit the 0.50 corr threshold — CTA at 0.635
  is still meaningfully uncorrelated vs v2, and its DSR/Sharpe/DD profile is superior.
  Do NOT re-tune parameters; grid burned.
- **Bollinger(20, k=2.5) mean reversion, upper_half exit, SMA200-gated** (E18, s11):
  mean WF Sharpe 0.896 (> v2 0.851), worst DD **-8.44%**, OOS Sharpe 0.989,
  **corr to v2 0.364 — lowest of any family tested.** Failed: DSR 0.848 (< 0.95,
  deflated across the 14-config session grid) and diff-vs-SPY CI [-0.821,+1.359]
  straddles zero; terminal $1k $2,297 << SPY $6,775 (low avg exposure raw-return
  giveaway). Condition to revisit: as ensemble diversifier ONLY if longer data
  yields a significance path; grid burned, no re-tuning, no standalone re-test.
- **Harry Browne Permanent Portfolio PP(band=0.10) SPY/TLT/GLD/SHY** (E14, s9): mean WF
  Sharpe **1.001** (highest multi-asset family ever tested), worst DD **-15.82%** (best
  ever), OOS Sharpe 0.896, **DSR 0.975 — passes deflation bar**. Failed: diff-vs-SPY
  CI [-0.575,+0.901] straddles zero; terminal $1k $4,308 vs SPY $8,283 (raw-return
  giveaway like RP — diversification hurts absolute return in a bull). Corr to v2: 0.430
  (< 0.50 threshold). Condition to revisit: as ensemble component if a v2/PP ensemble CI
  can clear zero (same path as E13 RP ensemble — that failed too; do NOT re-try ensemble
  unless 2+ more years of live data extend the sample meaningfully).
- **Trend-gated risk parity RP(lb60,b0.03) SPY/IEF/GLD** (E12, s8): mean WF
  Sharpe 1.018 (> v2 0.844), worst-fold DD **-7.6%** (new best), OOS Sharpe 1.291,
  **DSR 0.982 — FIRST family ever to pass the deflation bar.** Failed: diff-vs-SPY
  CI [-0.461,+1.629] straddles zero; unlevered raw return badly lags ($2,995 per
  $1k since 2000 vs SPY $6,768 — IEF/GLD late listings put early years in cash).
  Corr to v2: 0.467 OOS. Condition to revisit: as ensemble component if a
  significance path emerges on longer data; or standalone for a capital-
  preservation (not growth) mandate.
- **v2/RP fixed-mix ensemble** (E13, s8): best 30/70 mean WF Sharpe 1.085
  (highest ever tested), worst DD -7.7%, DSR 0.980. Failed: diff-vs-SPY CI
  [-0.269,+1.364] straddles zero AND terminal $1k $4,174 < SPY $6,768 (raw-return
  giveaway, same flaw as the GTAA ensemble). Condition to revisit: only if the
  live era or extended data shows the Sharpe edge translating into a diff-CI that
  clears zero; do NOT re-tune mixture weights (3 weights already burned).
- **GTAA(w150,b0) SPY/IWM/IEF/GLD** (E6, s6): mean WF Sharpe 0.892 (v2 0.844),
  worst-fold DD -12.6% — best risk profile tested to date, robust across 6 cfgs,
  but DSR 0.897 and diff-vs-SPY CI [-0.76,+0.98] fail the gate. Correlation with
  v2: 0.721 (M1 memo, s7) — above 0.70 threshold; ensemble $1k $6,542 vs v2 $9,258.
  Condition to revisit: only if correlation drops below 0.60 on more data, or if
  a fundamentally different sleeve with LOW correlation to v2 is found first.
- **GTAA-5(w200,b0.02) SPY/EFA/IEF/VNQ/DBC** (E10, s7): mean WF Sharpe 0.822,
  worst-fold DD **-9.9%** — best drawdown profile EVER tested (<v2's -20.5%), robust
  across 6 cfgs. DSR 0.7657 and diff-vs-SPY CI [-0.691,+0.991] fail gate (DBC history
  truncates fold-1 severely). Condition to revisit: after 3-5 more years of live DBC
  data extend fold-1 significance; or as ensemble component if v2 correlation proves
  lower on expanded data. Do NOT retry standalone — needs more DBC history to pass DSR.

## Watch-list additions (s13)
- No new watch-list entries this session. E22 Ensemble shows the strongest DD profile
  (−10.8%) and highest mean WF Sharpe (1.048) of any combination tested, but OOS
  correlation to v2 is 0.943 — far above the 0.70 new threshold. Relaxing ensemble
  threshold further not recommended without significance improvement.

## Session log
- 2026-07-23 s18 — Three new investing-philosophy experiments (per standing mandate).
  New mark $996.65 (2026-07-22 close, −0.116% day). v2 exposure 1.0; no trades.
  Guardrails ALL GREEN; drawdown from peak −0.98% (GREEN). Suite 79/79 (+16 tests).
  E26 Donchian Channel / Turtle Trading (Dennis & Eckhardt 1983, 4 cfg, reg id
  in hypotheses.jsonl): best DCH(S1,tv0.15) mean_wf=0.475 (<0.844 bar), worst DD
  −21.4%, DSR=0.9531 (passes), CI=[−0.703,+1.003] straddles zero, corr_v2=0.610.
  DISCARDED. Fold-1 Sharpe −0.158 — breakout signal caught bubble top without the
  SMA200 anchor to stay out of dot-com peak. Family PERMANENTLY CLOSED.
  E27 52-Week High Proximity (George & Hwang 2004, 4 cfg): best 52wk(H0.95,L0.85)
  mean_wf=0.634 (<0.844), worst DD −19.75% (better than v2), DSR=0.9452 (fails
  0.95 bar), CI=[−0.694,+0.690] straddles zero, corr_v2=0.937 (near-duplicate of v2).
  Critical finding: the 52-week high anchoring signal IS the SMA200 signal in
  disguise on a broad index — 0.937 correlation confirms near-identical information.
  DISCARDED. Family PERMANENTLY CLOSED.
  E28 ADX Trend Strength (Wilder 1978, 4 cfg): best ADX(p14,t20) mean_wf=0.797
  (<0.844), worst DD −18.45% (better than v2), DSR=0.856 (<0.95 bar), CI=[−0.841,
  +0.814] straddles zero, corr_v2=0.804. Notable: ADX(p14,t25) produced second-
  lowest DD ever (−9.65%, after CTA −6.19%) and OOS Sharpe 1.003, but fold-2
  Sharpe 0.463 (2010-2019 bull market exposes instability). DISCARDED, not watch-
  list eligible (DSR <0.95 and corr >0.50). Not closed — ADX concept could revisit
  as overlay in Phase 3 if capital-preservation mandate is separated.
  v2 significance re-check (ROADMAP #10): CI=[−0.0128,+0.7077], essentially
  unchanged (vs −0.0129 in s13). Lower bound improved by 0.0001. Next: August.
  $1k benchmark (2000→2026-07-22): v2 $8,381 > QQQ $6,946 > SPY $6,774 > DIA
  $6,759 > IWM $6,711 > EWC $5,768 > E28 $5,029 > E27 $4,864 > EFA $3,909 >
  ACWI $3,594 > E26 $2,105. v2 champion remains best realistic strategy found.
  Configs 180→192.
- 2026-07-22 s17 — Engineering session (queue exhausted; zero configs, 180
  unchanged). Built Phase-3 stress harness backtest/stress.py: bear-regime
  replay (dot-com/GFC/COVID/2022), doubled-cost runner (no-lookahead
  unit-tested), ±25% perturbation grid (v2 -> 9 configs), collapse verdict
  (Sharpe < 50% base or DD < -20%). 8 new tests, SYNTHETIC DATA ONLY — module
  forbidden from touching champion returns before Phase 3 (leakage guard).
  Suite 63/63. New mark $997.81 (2026-07-21 close, +0.834% day; SPY rebound on
  3M/GM earnings beats and semiconductor strength). Exposure 1.0; no trades;
  guardrails ALL GREEN. Notes: research/2026-07-22-s17-stress-harness.md.
- 2026-07-21 s16 — Second run of 2026-07-21. No new close; mark carried $989.56.
  Research queue exhausted (180 configs, 11 families closed) -> zero-config analysis:
  M3 exposure-profile memo (research/2026-07-21-s16-exposure-profile.md) answering
  Mr. Menendez's direct question on why the book holds only SPY. v2 is an
  index-timing strategy by design (SPY vs T-bill cash); historically 64.6% of days
  fully invested, 26.9% cash, avg exposure 0.716; avoided -29.8% (dot-com) and
  -31.8% (GFC) at the cost of ~8 missed +5-12% rallies. Exposure 1.0 confirmed;
  no trades; guardrails ALL GREEN; 55/55 tests. Configs unchanged 180.
- 2026-07-21 s15 — E25 Vigilant Asset Allocation (VAA, Keller & Keuning 2017).
  6 configs (n3/n4, bp=0.30/0.50/0.90). Best VAA(n3,bp0.50): mean WF 0.626 (< 0.844
  bar), worst DD −41.85% (>> −20.5% bar), DSR 0.9639 (passes), diff-CI [−0.653,+1.144]
  (straddles zero), corr v2 OOS 0.60 (> 0.50 watch-list threshold). DISCARDED.
  Interesting: terminal $9,202 > v2 $8,382 on raw return, driven by fold-3 OOS Sharpe
  0.982; but fold-2 (2010-2019 bull) Sharpe 0.409 reveals breadth-signal fragility at
  n=3 assets. VAA family PERMANENTLY CLOSED. Mark $989.56 (2026-07-20 close).
  Guardrails ALL GREEN. 55/55 tests. Configs 174→180.
- 2026-07-20 s14 — Maintenance run (second of the day; queue exhausted, no new
  close). FIX: s13 omitted its report file — reconstructed reports/2026-07-20.md
  from the log + commit 8880e2a; new ROADMAP standing item #21 (report file must
  exist before push). Correction: s13's "1 trading day stale" was wrong — Jul
  18/19 were the weekend, Friday's close landed in f573b04; cache CURRENT.
  Mark carried $991.16; exposure 1.0; no trades; guardrails ALL GREEN; 49/49
  tests (pytest+backtesting reinstalled in fresh sandbox). M2 standing intl
  benchmark panel (research/2026-07-20-s14-benchmark-panel.md, holdout-cut):
  from 2000 v2 $8,382 > QQQ $6,947 > SPY $6,775 > DIA $6,759 > EWC $5,768 >
  ACWI $3,595 > ^GDAXI $3,557 > ^GSPTSE $3,310 > ^N225 $2,087 > ^HSI $1,412 >
  ^FTSE $1,339; v2 DD −20.5% vs −50…−83% for indexes. From 2010: SPY/QQQ/DIA/
  ACWI beat v2 raw. From 2020: SPY/QQQ/^GDAXI/ACWI edge v2 raw; v2 DD half
  theirs. Canada trails everywhere. Do-nothing (2020→2025H): hold $1.90 vs
  strat $1.60 after tax — unchanged. ZERO configs burned (174).
- 2026-07-20 s13 — Three new investing-philosophy families per standing research mandate.
  Data 1 trading day stale (July 18 Action not yet committed); mark carried $991.16.
  Guardrails ALL GREEN; drawdown from peak −1.52% (GREEN). 49/49 tests passing.
  New files: strategies/market_breadth.py, strategies/low_vol_sector.py,
  strategies/ensemble.py + tests/test_market_breadth.py, tests/test_low_vol_sector.py.
  E22 v2+CTA Ensemble (3 cfg, reg 68d23093c3): relaxed corr threshold to 0.70 per
  roadmap item #5. Best 40/60 v2:CTA alpha: mean WF Sharpe 1.048, worst DD −10.8%,
  DSR 0.981 (PASSES) — but CI [−0.493,+1.225] straddles zero AND OOS corr v2=0.943
  (far above 0.70 threshold). DISCARDED. The high OOS corr is a new finding: the CTA
  SPY sleeve and v2 SPY are nearly identical in the 2020-2025H bull run; diversification
  only materializes in bear/crisis regimes (2000-2009 fold shows strong benefit, Sharpe
  1.109→1.170 and DD only −6%). Key insight: corr 0.635 measured in the single-asset
  comparison but blended OOS exposure → v2 dominance at alpha=0.40 still.
  E23 Market Breadth (6 cfg, reg 04d499088f): Fosback/Zweig sector-breadth gate on
  vol-targeted SPY. Best up=0.8/lo=0.5/vt=0.18: mean WF Sharpe 0.642, worst DD −24.2%,
  DSR 0.480 (FAILS). DISCARDED, family CLOSED. Critical finding: sector breadth (fraction
  of XLK/XLF/XLE/XLV/XLY/XLP/XLI/XLU/XLB above SMA200) is 0.901 correlated to v2 OOS
  — breadth IS v2 in different form. The SMA200 gate on the index captures all the
  breadth information because sectors and the index move together. Fold 1 (2000-2009)
  Sharpe only 0.478 — the breadth threshold triggers were too slow during the dot-com
  crash; sectors stayed low-breadth while the recovery lagged.
  E24 Low-Vol Sector Rotation (6 cfg, reg f66e6c1949): Baker & Haugen / Frazzini &
  Pedersen low-vol anomaly applied to 9 sector ETFs monthly. Best n=5/no gate: mean WF
  Sharpe 0.589, worst DD −48.0%, DSR 0.464 (FAILS). DISCARDED, family CLOSED. Fold 1
  (2000-2009) Sharpe only 0.135-0.217 — utility/consumer staple "low-vol" sectors
  still crashed −37-48% in 2001-2002. The anomaly requires individual stock selection
  across a much larger universe (500+ stocks) to work; sector ETFs are too broad and
  too few for this effect. Gate adds no benefit: gated (SMA200) max WF Sharpe 0.530
  vs ungated 0.589.
  ROADMAP #10 v2 re-check: CI [−0.0129,+0.7077] — still straddles zero; lower bound
  improved marginally vs s12 (−0.009 → −0.013 in the other direction, explained by
  added deflation from 174 cumulative configs). DSR 0.703 (against 48 session trial
  sharpes). Full significance still requires more live data.
  $1k tests (2000→2026-07-17): v2 $8,382 > E22 Ensemble $5,294 > QQQ $7,458 > SPY
  $7,050 > DIA $6,989 > IWM $6,473 > E24 LowVol $6,539 > E23 Breadth $3,811.
  Note: Ensemble terminal value ($5,294) below v2 ($8,382) because CTA gives away bull-
  market returns (expected tradeoff for lower DD; for capital preservation mandate, the
  Ensemble remains superior). Configs 159→174.

- 2026-07-18 s12 — Two new investing philosophy families beyond the charter queue.
  New mark $991.16 (2026-07-17 close, −0.990% day, −0.884% all-time). v2 exposure 1.0
  confirmed; 20d vol 12.2% < 18% target. Guardrails ALL GREEN; drawdown from peak −1.52%.
  New strategies: strategies/cta_trend.py (Multi-Asset CTA Trend, AQR managed-futures
  replication) + strategies/seasonal.py (Halloween Effect, Bouman & Jacobsen 2002).
  E20 CTA (6 cfg, 10 configs total session): best CTA(SPY/IEF/GLD,vt0.12) mean WF
  Sharpe 1.099 (NEW ALL-TIME RECORD), worst DD −6.19% (NEW ALL-TIME RECORD), OOS Sharpe
  1.112, DSR 0.9787 (passes) — but diff-vs-SPY CI [−0.588,+1.302] straddles zero, and
  corr_v2 0.635 > 0.50 watch-list threshold → DISCARDED (not watch-list eligible per
  current ensemble rules). Other CTA configs: all show mean WF 0.869–1.099; all pass DSR;
  none clear the CI. SPY/IEF/GLD combination superior to SPY/TLT/GLD (IEF less volatile
  in 2022 rising-rate regime). CTA is STRONGLY preferred for capital-preservation
  mandates — see watch-list section below.
  E21 Seasonal (4 cfg): best Seas(Oct-Apr,out=0.3) mean WF 0.892, DD −18.11%, DSR 0.9267
  (FAILS 0.95 bar), CI straddles zero, corr_v2 0.917 (near-duplicate of v2). DISCARDED,
  family CLOSED — the SMA200 trend gate already handles the seasonal timing; adding a
  calendar gate is a diluted v2 at high correlation.
  Benchmarks $1k 2000→2026-07-17: v2 $8,382 > QQQ $6,947 > SPY $6,775 > DIA $6,759.
  Mag-7 eqw from 2012 → $63,681 (survivorship-biased; G4 concentration limit prevents
  single-stock overweight in live portfolio). Configs 149→159.
- 2026-07-17 s11 — Mean reversion, the LAST unexplored charter family (RSI-2,
  Bollinger, IBS as candidate NEW SLEEVE; frozen v2 untouched). 8-source
  research pass (Connors/QuantifiedStrategies, Price Action Lab skeptic,
  Pagonidis NAAIM IBS, SSRN 5713082, Atlantis Bollinger, Alvarez decay, MDPI
  costs, QuantVero). New strategies/mean_reversion.py + 5 tests (suite 39/39).
  New mark $1,001.07 (2026-07-16 close, −0.542% day, SPY identical; first live
  down day). Guardrails ALL GREEN. E17 RSI2 (6 cfg, 36774e62aa): best e5/x80
  mean WF 0.756, DD −7.9%, DSR 0.485 → DISCARDED, family closed (decay pattern
  confirms the data-mining prior). E18 Bollinger (4 cfg, c8b45926ea): best
  k2.5/upper_half mean WF 0.896, DD −8.4%, DSR 0.848, CI straddles →
  DISCARDED but WATCH-LISTED (corr 0.364, lowest ever). E19 IBS (4 cfg,
  d714733f08): best e0.1/x0.8 mean WF 0.244, DD −22.8%, DSR 0.616 →
  DISCARDED, family CLOSED (EOD fill gives away the overnight edge). After-tax
  do-nothing unchanged: B&H wins 2020-2025H $1.94 vs $1.61. Configs 135→149.
  CHARTER QUEUE COMPLETE (9/9 families explored).
- 2026-07-16 s10 — Second run of 2026-07-16. No new close (newest usable SPY
  close still 2026-07-15); mark carried $1,006.52, exposure 1.0 re-confirmed,
  no trades. Session work: last unexplored charter queue item — famous-failures
  risk guardrails. 7-source research pass (Fed History & PWG on LTCM; WaPo/
  SteadyOptions on Niederhoffer; Khandani-Lo NBER 14465 on Quant Quake;
  Chincarini SSRN 1633589 on Amaranth; CFTC/PWG best practices). Built
  backtest/guardrails.py (G1-G7, reporting-only) + 12 tests; suite 34/34.
  Live book verdict: ALL GREEN. ENGINEERING session — no pre-registration, no
  configs burned (135 unchanged), champion untouched. Roadmap gains standing
  item #14 (guardrails at every mark).
- 2026-07-13 s1 — Scaffold; SMA trend grid; champion v1 = SMA200/b3. KEPT.
- 2026-07-13 s2 — Roadmap #2+#3 (+#1 attempt). Built fractional vector engine
  (validated vs backtesting.py), vol_target strategy, rf-cash accounting;
  acquired VIX 1990→2026-07. E1 rf-cash OOS Sharpe 0.914; E2 vt18/lb20 0.925
  (neighbors 0.920-0.939); E3 both 0.967, MaxDD -17.9%. KEPT E3 as v2.
  Caveats: tv at grid edge; rf gain regime-dependent. Initialized portfolio.
  Negative: tv 0.10-0.12 over-delevers IS (Sharpe 0.69-0.76).
- 2026-07-14 s4 — First live-data session. Fixed data_freshness() tz crash
  (15/15 tests). MIGRATION MARK: live track re-based to real SPY, $999.00 @
  749.17, exposure 1.0, no trade; live clock started. Re-baselined all
  benchmarks on real data at 0.15% costs (END-GOAL bar). E1 (25d3eaf2fb,
  12 cfg): tv=0.18 confirmed plateau, not artifact — no wider config beats v2
  (all 0.81-0.84); no change. E2 (d5c820392c, 6 cfg): VIX percentile overlay
  FAILED pre-registered bar (DD -1.27pts < 2; DSR 0.9455; CI straddles 0) —
  all DISCARDED, as the skeptical prior predicted. Honest findings: v2's edge
  vs SPY not yet statistically significant; after-tax do-nothing won 2020-2025H.
- 2026-07-14 infra — Fixed the "no live data" wall: built self-refreshing
  GitHub Actions data pipeline (2000→present, 28 tickers, verified). Added
  multi-asset loader, deflated-Sharpe + bootstrap significance + after-tax /
  do-nothing evaluation, pre-registration harness with config cap. FROZE
  champion v2 and entered Phase 2 (live clock started). Archived legacy
  MACD/AMZN prototype to archive/. Testing protocol → 2000-present walk-forward
  with a locked final 12-month holdout. No strategy experiments this session.
- 2026-07-14 s5 — Philosophy expansion. Built multi_engine.py (multi-asset
  portfolio returns). Implemented 3 new strategies: dual_momentum.py (Antonacci
  2014 GEM), drawdown_kill.py (kill-switch overlay on v2), sector_momentum.py
  (cross-sectional XL* sector rotation). All 3 DISCARDED:
  E3 Dual Momentum (6 cfg): DSR=0.741, CI=[-0.90,+0.47], worst DD -42.6% — all bars
  missed; TLT harbor failed in 2022 rising-rate regime.
  E4 Kill-Switch (4 cfg): DSR=0.898, max-fold Sharpe drop 0.176 (>0.08 bar) — whipsaw
  at -15% trigger inside v2's normal DD range; concept sound but parameters too tight.
  E5 Sector Momentum (4 cfg): DSR=0.685, fold-1 Sharpe=0.090, worst DD -51.8% —
  momentum crash in 2000-2009 dot-com fold (XLK dominated entering bubble top).
  $1k test: v2 $8,374 > SPY $7,043 > DIA $7,008 > QQQ $7,417. v2 wins all realistic
  benchmarks. No portfolio change. Cumulative registered configs: 46.
- 2026-07-14 s6 — Roadmap items 1-3. New strategies/gtaa.py (+3 causality
  tests, 18/18 pass). E6 GTAA (5d45ec36b7, 6 cfg): best w150/b0 mean WF 0.892,
  worst DD -12.6% — best risk profile to date but DSR 0.897 / CI straddles 0 →
  DISCARDED, moved to watch-list as future ensemble diversifier. E7 DM-SHY
  (cfc6112ed7, 4 cfg): mean 0.539, DD -36.7% → DISCARDED; dual momentum 0-for-2,
  rotation itself (not just TLT harbor) is the failure. E8 kill-switch -20/-10
  (f117a77dbb, 2 cfg): zero DD improvement, fold-2 Sharpe -0.095 → DISCARDED;
  kill-switch item closed permanently (vol targeting already de-risks).
  Do-nothing check unchanged: after-tax B&H won 2020-2025H ($1.92 vs $1.59).
  No new close (cache still 2026-07-13); mark unchanged $999.00, no trades.
  Cumulative registered configs: 58.
- 2026-07-15 s7 — Roadmap items 0 and 4; GTAA correlation memo (item 2).
  New strategies: gem.py (True Antonacci GEM, international), sector_trend.py
  (sector momentum + per-sector SMA200 gate). First live P&L: +$3.55 (+0.355%).
  E9 True GEM SPY/EFA/EEM→AGG (5e83ad9d86, 6 cfg): best lb126/sk0 mean WF 0.435,
  DD -32.5%, DSR=0.301, CI=[-1.175,+0.319] → DISCARDED. International rotation
  underperformed badly in fold-2 (2010-2019 US bull market); EEM/EFA drag was severe.
  E10 GTAA-5 SPY/EFA/IEF/VNQ/DBC (c6a6ffb9c0, 6 cfg): best w200/b0.02 mean WF 0.822,
  DD -9.9% (best ever!), DSR=0.766, CI=[-0.691,+0.991] → DISCARDED on significance.
  Added to watch-list; DBC history truncates fold-1 severely, DSR can't clear gate yet.
  E11 Sector+Trend gate (fa06fbdf2b, 6 cfg): best lb252/n1 mean WF 0.235, DD -47.4%,
  DSR=0.652 → DISCARDED. Trend gate did NOT fix E5 failure; worst DD still -47.4%.
  Sector family closed permanently (both E5 standalone and E11 trend-gated failed).
  M1 Correlation memo: v2/GTAA-4 correlation 0.721 (>0.70 threshold). 50/50 ensemble
  OOS Sharpe 0.946 but $1k = $6,542 vs v2 $9,258 — raw return drag too large.
  Ensemble not recommended at current correlation. $1k test (2000→2026-07-14):
  v2 $9,257.88 > QQQ $9,014.44 > SPY $8,249.83 > DIA $8,138.90. v2 wins.
  Champion v2 unchanged. Cumulative registered configs: 94.
- 2026-07-16 s9 — Three new investing philosophy experiments. Data fresh through
  2026-07-15 (SPY $754.81, cache stale_days=0). New mark: portfolio $1,006.52
  (+$3.97, +0.396% from s8; +0.652% all-time). v2 exposure 1.0 re-confirmed; no trades.
  New strategies: permanent_portfolio.py (fixed-slot PP, CRITICAL BUG FOUND AND FIXED:
  original draft allocated 100% SPY during 2000-2002 pre-listing warmup; correct version
  caps each slot at 25% permanently); blended_momentum.py (multi-lookback composite);
  adaptive_alloc.py (top-N momentum + min-variance weights).
  E14 Permanent Portfolio (4 cfg, reg 6c4760e6e5): best PP(band=0.10) mean WF Sharpe
  1.001, worst DD -15.82% (best ever across ALL families), OOS Sharpe 0.896, DSR 0.975
  — SECOND DSR PASS (after RP). But diff-vs-SPY CI [-0.575,+0.901] straddles zero AND
  terminal $4,308 < SPY $8,283 → DISCARDED; WATCH-LISTED (corr 0.430 to v2).
  E15 Blended Momentum (6 cfg, reg 884635fab0): best BM(n_lb=2,tv=0.18) mean WF 0.688,
  worst DD -18.15%, DSR 0.981 — PASSES but CI [-0.537,+1.093] straddles zero AND
  corr 0.879 with v2 (near-duplicate). DISCARDED. Blended momentum family closed — it's
  a diluted v2; the binary SMA200 gate is better than a graded composite signal.
  E16 Adaptive Asset Allocation (6 cfg, reg 091d3fbc16): best AAA(top3,lb12mo) mean WF
  0.682, worst DD -47.64% (terrible), DSR 0.918, CI straddles zero → DISCARDED. AAA
  without a trend gate suffers the same momentum-crash problem as E5 sector rotation
  and E3 dual momentum. The family is CLOSED.
  Cumulative registered configs: 135. No new close (mark date 2026-07-15).
  $1k sim (2000→2026-07-15 fresh data): v2 $9,294 > IWM $9,075 > QQQ $8,990 >
  SPY $8,283 > DIA $8,158 > AAA $7,705 > PP $4,873 > BlendMom $4,459.
- 2026-07-15 s8 — Roadmap item 5 (risk parity) + ensemble revisit (trigger met:
  corr < 0.50). New strategies/risk_parity.py (+4 causality tests, 22/22 pass;
  installed pytest/backtesting in fresh sandbox). No new close (cache still
  2026-07-14); mark carried $1,002.55, no trades, exposure 1.0 re-confirmed.
  E12 RP SPY/IEF/GLD (64e6e20d9c, 6 cfg): best lb60/b0.03 mean WF 1.018, worst
  DD -7.6% (best ever), OOS Sharpe 1.291, DSR 0.9823 — FIRST DSR PASS — but
  diff-vs-SPY CI [-0.461,+1.629] straddles zero → DISCARDED per pre-registered
  bar; watch-listed. E13 v2/RP ensemble (082d45e3fc, 3 cfg): best 30/70 mean WF
  1.085 (highest ever), DD -7.7%, DSR(9 trials) 0.9797, but CI [-0.269,+1.364]
  fails AND $1k $4,174 < SPY $6,768 → DISCARDED; watch-listed. Do-nothing check
  unchanged: after-tax B&H won 2020-2025H ($1.94 vs $1.61 per $1). Intl
  benchmark panel first computed: v2 $9,258 beats SPY/QQQ/EWC/ACWI from 2000;
  QQQ/SPY/EWC/ACWI all beat v2 from 2010 and 2020 (bull-market lag, expected).
  Cumulative registered configs: 103.
