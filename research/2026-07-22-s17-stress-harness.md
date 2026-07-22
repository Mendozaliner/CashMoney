# s17 (2026-07-22) — Phase-3 stress-test harness (engineering, zero configs)

## Why now
The research queue is exhausted (180 configs, 11 families closed) and the live
clock is the binding constraint until August. The highest-value non-config work
is making Phase 3 executable in one session when (if) v2 graduates: the charter
requires bear-regime replay, doubled costs, and ±25% parameter perturbation.
None of that tooling existed until today.

## What was built — backtest/stress.py (+8 tests, suite 63/63)
1. **regime_replay(returns, benchmark, windows)** — metrics (total return,
   ann. Sharpe, max DD, n_days) inside the four charter bear windows:
   dot-com 2000-03-24→2002-10-09, GFC 2007-10-09→2009-03-09,
   COVID 2020-02-19→2020-03-23, 2022 bear 2022-01-03→2022-10-12.
   Empty overlap reports n_days=0 so silence can't be read as passing.
2. **costed_returns(exposure, asset_returns, ...)** — exposure applied to the
   NEXT day's return (unit-tested no-lookahead), turnover-based costs at the
   standard 0.15% with a cost_multiplier (Phase 3 uses 2.0). Doubling costs
   exactly doubles drag (unit-tested).
3. **perturbation_grid(params, pct=0.25)** — one-at-a-time ±25% plus the four
   corners for 2-parameter strategies. For v2 (target_vol=0.18, lookback=20)
   this yields exactly 9 configs: tv ∈ {0.135, 0.18, 0.225} × lb ∈ {15, 20, 25}.
4. **collapse_verdict(base, stressed)** — charter collapse test codified:
   COLLAPSE if any stressed run's Sharpe < 50% of base or max DD < −20%.

## Discipline
Tested on SYNTHETIC data only. The module docstring forbids running it on
champion returns before Phase 3 is declared — running perturbations on v2 now
would be tuning-adjacent data leakage into the very test meant to be fresh at
graduation. Zero configs pre-registered or burned (180 unchanged).

## References
- López de Prado, *Advances in Financial Machine Learning* (2018), ch. 14
  (backtest overfitting / strategy stress paths).
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio" (already in
  backtest/evaluation.py; the perturbation grid deliberately reuses the same
  skeptical framing: robustness across neighborhoods, not best points).
- Charter Phase-3 spec (SKILL.md): regimes, 2× costs, ±25% perturbation.
