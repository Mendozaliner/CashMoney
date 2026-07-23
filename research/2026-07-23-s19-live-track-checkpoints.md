# S19 memo — Live-track checkpoint methodology (zero-config engineering)

Date: 2026-07-23 (second session of the day; s18 ran experiments this morning).
Scope: NO new configs (192 unchanged). Reporting-only tooling for the
Phase-2 graduation review (~2026-08-13 first checkpoint, per ROADMAP #9).

## What was built
`backtest/live_track.py` + 8 synthetic-only tests (suite now 87/87):
- `daily_marks()` — collapses portfolio.json history to one value per
  mark date (carried marks dedupe, last wins).
- `monthly_checkpoints()` — completed-calendar-month live vs SPY returns
  since the 2026-07-13 baseline; in-progress month excluded.
- `consecutive_beats()`, `worst_drawdown()` — criteria 2 and 3 counters.
- `min_track_record_length()` — PSR-based MinTRL (Bailey & Lopez de
  Prado 2012): observations needed before an observed positive Sharpe is
  statistically distinguishable from a benchmark at 95%.
- `summary()` — one-call scoreboard for reports/briefings.

## First run on the real live track (2026-07-22 close)
- Completed months: 0 (July in progress; first checkpoint after July ends).
- Worst live drawdown: −1.69% (peak $1,006.52 → $989.56). Criterion 3: PASS so far.
- Live obs: 8 marks. MinTRL vs SPY: **infinite** — correctly so: v2 has been
  fully invested (exposure 1.0) for the entire live window, so live
  strategy-minus-SPY differences are ~0 and there is no live edge to measure yet.

## Honest implications (worth stating plainly)
1. The live exam can only differentiate v2 from SPY when the strategy goes
   defensive (trend gate off or vol scaling < 1). In a calm up-market the live
   track will match SPY minus nothing, and "3 months of beating SPY" may hinge
   on rounding. The desk should expect the August checkpoint to be a coin flip
   unless volatility picks up.
2. Literature check: PSR/MinTRL math says 3 months of daily data cannot
   statistically prove an edge of v2's size — typical MinTRL for
   Sharpe-difference tests runs years, not months (Bailey & LdP 2012; the
   five-year rule of thumb for IR≈1 strategies). Phase 2 therefore proves
   PROCESS FIDELITY (the system marks honestly, trades as specified, respects
   risk limits live), while the STATISTICAL case continues to rest on the
   26-year walk-forward CI (roadmap #10, monthly re-check). Both are required;
   neither substitutes for the other.
3. Standing use: run `live_track.summary()` at every mark; first completed-month
   checkpoint prints automatically in the first August session.

## Sources
- Bailey & Lopez de Prado (2012), The Sharpe Ratio Efficient Frontier, SSRN 1821643
  (also davidhbailey.com/dhbpapers/sharpe-frontier.pdf).
- Bailey & Lopez de Prado (2014), The Deflated Sharpe Ratio, SSRN 2460551.
- Portfolio Optimizer blog, "The Probabilistic Sharpe Ratio ... Minimum Track
  Record Length" and the companion post on Sharpe-difference MinTRL.
- Lopez de Prado, QWAFAFEW Boston deck, "Deflating the Sharpe Ratio by asking
  for a Minimum Track Record" (2017).
- AlgoTrading101, "What is a Good Track Record in Trading?" (5-year rule of thumb).
- TradersSecondBrain, "How Many Trades to Know If a Strategy Works" (trade-count
  vs calendar-time framing).
