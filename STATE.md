# STATE — CashMoney research system

Updated: 2026-07-13 (session 1)

## Environment constraints (discovered session 1)
- Research sandbox: only github.com reachable; all market-data APIs blocked.
- Data source: committed snapshot of SteelCerberus/us-market-data —
  daily SPY total-return proxy, 1885-03-20 -> 2025-12-19 (`data/cache/us_market_data.csv`).
  Refresh via `data.loader.refresh_spy_proxy_cache()`.
- Benchmarks DIA, QQQ, Mag-7: NOT AVAILABLE yet (no multi-asset data). SPY B&H only.

## Champion
**sma_trend(window=200, band=0.03)** — long SPY-proxy when Close > 1.03×SMA200,
flat when Close < 0.97×SMA200, else hold state. Costs 0.1%/side, cash yields 0%.

## Baselines & champion metrics (this dataset, costs included)
| Config | Period | CAGR % | Sharpe | Sortino | MaxDD % | Trades/yr | $1k -> |
|---|---|---|---|---|---|---|---|
| SPY B&H | IS 2010-2019 | 13.20 | 0.918 | 1.149 | -19.35 | 0.1 | 3450 |
| SMA200/b3 | IS 2010-2019 | 8.54 | 0.763 | 0.867 | -20.45 | 0.6 | — |
| SPY B&H | OOS 2020 -> 2025-12-19 | 14.91 | 0.774 | 0.951 | -33.72 | 0.2 | 2290 |
| **SMA200/b3** | OOS 2020 -> 2025-12-19 | 11.49 | **0.871** | 0.957 | **-20.76** | 0.8 | 1913 |
| SPY B&H | T12M (2024-12-19 -> 2025-12-19) | — | — | — | -18.76 | — | 1155.57 |
| SMA200/b3 | T12M | — | — | — | -10.69 | — | 1089.06 |

Keep/revert precedent: champion selected in-sample by neighborhood-average Sharpe
(robustness), kept because OOS Sharpe 0.871 > B&H 0.774 and OOS MaxDD improved.

## Session log
- 2026-07-13 — Scaffolded repo (strategies/backtest/data/research/reports/tests).
  Built SMA trend filter w/ hysteresis band (Faber 2007; Zakamulin 2014/2018).
  Grid 6 windows × 4 bands IS 2010-2019; picked SMA200/b3 by neighborhood Sharpe.
  KEPT (first champion). No-lookahead unit tests added (causality + t+1 execution
  + cost application). Data pipeline limitation documented.
