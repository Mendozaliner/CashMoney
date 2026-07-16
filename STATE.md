# STATE — CashMoney research system

Updated: 2026-07-16 s10 (famous-failures guardrails codified: backtest/guardrails.py G1-G7, 34/34 tests, live book ALL GREEN. No experiments — engineering session; configs stay 135. Mark carried $1,006.52, no new close)

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
**Latest mark (2026-07-15 close, session 9):**
1.333476 SPY × $754.81 = **$1,006.52** (+0.652% all-time from $1,000 inception).
v2 exposure confirmed 1.0 (754.81 > SMA200+3% band; 20d vol within 18% target). No trades.

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
**Current value: $1,002.55** (2026-07-14 close, session 7 mark). 1.333476 SPY units
@ $751.83. All-time: +$2.55 / +0.255% from $1,000 inception. No rebalance needed;
exposure 1.0 confirmed.

## Watch-list (not adopted; revisit under stated conditions)
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

## Session log
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
