# ROADMAP (reprioritized 2026-07-13)

1. **Multi-asset data pipeline.** Find/mirror a GitHub-hosted daily OHLCV dataset
   (or several) covering QQQ, DIA, IWM, sector ETFs, TLT/IEF/GLD and Mag-7 stocks
   through 2025+; commit snapshots to data/cache/. Unblocks: proper benchmark
   suite (DIA/QQQ/Mag-7), dual momentum, risk parity. Also refresh the
   us-market-data snapshot each session (upstream updates sporadically).
2. **Cash yield on flat periods.** Dataset already carries a daily risk-free
   series; credit T-bill return while out of the market (Faber's assumption).
   Measure effect on champion OOS Sharpe.
3. **Volatility targeting overlay** on the champion (scale exposure to hit a
   vol target, cap 1.0) — research queue item; single-asset friendly.
4. Dual momentum (Antonacci) — blocked on item 1.
5. Regime filters (VIX via datasets/finance-vix repo) — partial data available.
6. Cross-sectional momentum (Jegadeesh-Titman) — blocked on item 1.
7. Drawdown-control / risk-limit guardrails (LTCM/Niederhoffer lessons).

## Backlog of negative results to avoid re-testing
- Raw daily SMA crossover (band=0): dominated by banded variants at 0.1% costs.
- 50d windows: noise-dominated on daily SPY.
