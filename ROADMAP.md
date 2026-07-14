# ROADMAP (reprioritized 2026-07-13 session 2)

1. **Vol-target grid widening.** Extend tv to 0.21-0.30 and lb to 120 to test
   whether v2's tv=0.18 is a grid-edge artifact (as tv→∞, E2 → v1). Re-run
   keep/revert on the wider neighborhood.
2. **VIX regime filter** — data now local (data/cache/vix_daily.csv, through
   2026-07-10). Threshold / percentile scaling; compare & combine with v2.
   Note VIX dates extend past SPY-proxy data end (2025-12-19); align indexes.
3. **Multi-asset data pipeline** (carry-over). GitHub API blocked; try more
   candidate repos by name for QQQ/DIA/sector-ETF/Mag-7 daily OHLCV; recheck
   us-market-data for updates past 2025-12-19 each session.
4. Dual momentum (Antonacci) — blocked on item 3.
5. Cross-sectional momentum (Jegadeesh-Titman) — blocked on item 3.
6. Drawdown-control / risk-limit guardrails (LTCM/Niederhoffer lessons).
7. Position sizing: fractional Kelly on champion.

## Backlog of negative results to avoid re-testing
- Raw daily SMA crossover (band=0): dominated by banded variants at 0.1% costs.
- 50d SMA windows: noise-dominated on daily SPY.
- Vol targets ≤0.12 on trend-gated SPY: over-delever the IS bull decade
  (Sharpe 0.69-0.76 vs 0.765 champion v1); worst with lb=20 (turnover cost).
