# STATE — CashMoney research system

Updated: 2026-07-13 (session 2)

## Environment constraints
- Research sandbox: only github.com reachable (git protocol); GitHub REST API
  and all market-data APIs blocked.
- Primary data: snapshot of SteelCerberus/us-market-data — daily SPY
  total-return proxy + T-bill return index, 1885-03-20 → 2025-12-19
  (`data/cache/us_market_data.csv`). Upstream NOT updated since session 1;
  refresh attempted each session via `data.loader.refresh_spy_proxy_cache()`.
- NEW (session 2): daily VIX OHLC 1990 → 2026-07-10 from datasets/finance-vix
  (`data/cache/vix_daily.csv`, `data.loader.load_vix()`).
- Benchmarks DIA, QQQ, Mag-7: still NOT AVAILABLE (no multi-asset OHLCV found).

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
