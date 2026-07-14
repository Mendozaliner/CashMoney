# STATE — CashMoney research system

Updated: 2026-07-14 s6 (GTAA sleeve candidate, DM-SHY retry, conservative kill-switch — all discarded; GTAA on ensemble watch-list)

## PHASE 2 — PROVE (entered 2026-07-14)
Champion **v2 is FROZEN** as the live exam strategy. The live-outperformance
clock starts **2026-07-14** (first fresh mark once the data Action has run;
3 consecutive months of beating SPY, MaxDD < 20%, is the Phase-2 bar).
All new research runs in SEPARATE SLEEVES and must NOT touch the frozen live
track. Champion changes are allowed only if v2 decisively fails (trails SPY by
>5% over 6+ weeks live). See SKILL.md for keep/revert + significance gates.

## Graduation tracker (updated 2026-07-14 s5)
1. Beats S&P risk-adjusted OOS: POINT-PASS / SIGNIFICANCE-FAIL — 2020-2025H
   diff CI [-0.56,+0.89] straddles 0. FULL-SAMPLE update (s6b, 2000→2025-07,
   n=6,418 days): diff CI [-0.009,+0.708] — misses clearing zero by 0.009.
   Tantalizingly close but NOT passed; do not round up. Ensemble diversification
   is the likeliest way to push the lower bound through zero.
2. Live 3-mo outperformance: clock STARTED 2026-07-13 mark (0/3 months).
3. MaxDD < 20%: live 0.0%; worst backtest fold -20.5% (borderline — watch).
4. Full costs (0.15%/trade): PASS — negligible drag at ~2 trades/yr.
Phase-transition: not met (needs 3 live months + significance on #1).

## Live track baseline (migration 2026-07-14)
Portfolio re-based from SPY_PROXY (stale, ended 2025-12-19) to real SPY cache:
$999.00 carried, 1.333476 SPY units @ 749.17 (2026-07-13 close). Live clock and
all live-vs-SPY comparisons measure from this mark. Costs standard now 0.15%.

## Standing briefing instructions (per Mr. Menéndez, 2026-07-14)
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
buy-and-hold won ($1.92 vs $1.56 per $1). $1k test (2000→2026-07-13): v2 $8,374 vs
SPY $7,043, DIA $7,008, QQQ $7,417 — v2 wins on Sharpe AND terminal value. Legacy PROXY-data table below kept for history.

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
2026-07-13, fully invested per v2 (exposure 1.0), value $999.00 after entry
cost, marked at dataset close 2025-12-19 (stale-data caveat in file).

## Watch-list (not adopted; revisit under stated conditions)
- **GTAA(w150,b0) SPY/IWM/IEF/GLD** (E6, s6): mean WF Sharpe 0.892 (v2 0.844),
  worst-fold DD -12.6% — best risk profile tested to date, robust across 6 cfgs,
  but DSR 0.897 and diff-vs-SPY CI [-0.76,+0.98] fail the gate. Condition to
  revisit: as ensemble diversifier once any sleeve clears significance, or
  low-correlation memo (roadmap #2) motivates a combined-sleeve registration.

## Session log
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
