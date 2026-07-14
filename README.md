# CashMoney — Menéndez Capital research desk

A private algorithmic **trading-strategy research system**. It researches ideas
from the quant literature, backtests them honestly, tracks a live $1,000 paper
portfolio, and reports daily. It does **not** trade real money — the goal is to
produce evidence trustworthy enough that a human can decide whether to.

## What it actually does
- **Data** — daily OHLCV for a broad universe (index & sector ETFs, defensives,
  mega-caps, VIX, T-bill yield), 2000→present, in `data/cache/ohlcv/`. Refreshed
  every weekday by a GitHub Action (`.github/workflows/update-data.yml` →
  `scripts/fetch_data.py`) running on GitHub's servers, because the research
  sandbox can only reach github.com. Read it via `data.loader.load_ohlcv()` /
  `load_universe()`.
- **Strategies** — one module per idea in `strategies/` (common signal
  interface). Current frozen champion: a volatility-targeted trend filter.
- **Backtest** — `backtest/engine.py` (binary long/flat, backtesting.py) and
  `backtest/vector_engine.py` (fractional exposures), with realistic costs and a
  no-lookahead contract enforced by tests.
- **Honesty layer** — `backtest/evaluation.py`: deflated Sharpe ratio (penalizes
  the number of configurations tried), bootstrap confidence intervals on the
  strategy-minus-SPY edge, and after-tax / "would doing nothing have been
  better?" comparisons. `research/preregister.py` forces a written hypothesis
  and success bar before each experiment and caps configs per idea.

## How a strategy earns trust
Testing runs **walk-forward** across 2000-2009 / 2010-2019 / 2020-present with a
**locked final 12-month holdout** never touched until a candidate graduates. A
new idea is adopted only if it clears its pre-registered bar: deflated Sharpe
≥ 0.95 **and** a bootstrap difference-vs-SPY interval that excludes zero **and**
drawdown no worse than the incumbent. Most ideas are expected to fail — that is
the point.

Graduation (see `SKILL.md`) requires all of: beats SPY out-of-sample on
risk-adjusted return; the live paper portfolio beats SPY for 3+ consecutive
months; max drawdown stays < 20%; results survive doubled costs and ±25%
parameter perturbation.

## Layout
```
data/           loader + committed data cache (ohlcv/, manifests)
strategies/     one module per strategy
backtest/       engines + evaluation (stats/tax honesty layer)
research/       dated experiment scripts, notes, pre-registration log
reports/        one-page dated session reports
tests/          no-lookahead + engine + evaluation tests
archive/        legacy single-stock MACD prototype (not part of the system)
STATE.md        current phase, champion, metrics, session log
ROADMAP.md      prioritized backlog
```

*Research tooling only. Nothing here executes real trades or constitutes
financial advice.*
