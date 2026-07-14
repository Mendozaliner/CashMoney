# STATE — CashMoney research system

Updated: 2026-07-14 (infrastructure session — data pipeline + statistical honesty layer)

## PHASE 2 — PROVE (entered 2026-07-14)
Champion **v2 is FROZEN** as the live exam strategy. The live-outperformance
clock starts **2026-07-14** (first fresh mark once the data Action has run;
3 consecutive months of beating SPY, MaxDD < 20%, is the Phase-2 bar).
All new research runs in SEPARATE SLEEVES and must NOT touch the frozen live
track. Champion changes are allowed only if v2 decisively fails (trails SPY by
>5% over 6+ weeks live). See SKILL.md for keep/revert + significance gates.

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

## Baselines & champion metrics (vector engine, costs included)
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

## Session log
- 2026-07-13 s1 — Scaffold; SMA trend grid; champion v1 = SMA200/b3. KEPT.
- 2026-07-13 s2 — Roadmap #2+#3 (+#1 attempt). Built fractional vector engine
  (validated vs backtesting.py), vol_target strategy, rf-cash accounting;
  acquired VIX 1990→2026-07. E1 rf-cash OOS Sharpe 0.914; E2 vt18/lb20 0.925
  (neighbors 0.920-0.939); E3 both 0.967, MaxDD -17.9%. KEPT E3 as v2.
  Caveats: tv at grid edge; rf gain regime-dependent. Initialized portfolio.
  Negative: tv 0.10-0.12 over-delevers IS (Sharpe 0.69-0.76).
- 2026-07-14 infra — Fixed the "no live data" wall: built self-refreshing
  GitHub Actions data pipeline (2000→present, 28 tickers, verified). Added
  multi-asset loader, deflated-Sharpe + bootstrap significance + after-tax /
  do-nothing evaluation, pre-registration harness with config cap. FROZE
  champion v2 and entered Phase 2 (live clock started). Archived legacy
  MACD/AMZN prototype to archive/. Testing protocol → 2000-present walk-forward
  with a locked final 12-month holdout. No strategy experiments this session.
