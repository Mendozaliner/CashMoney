# Famous quant failures → codified risk guardrails (s10, 2026-07-16)

Queue item: "lessons from famous failures (LTCM, Niederhoffer, 2007 quant quake) as risk-limit guardrails."
This is an ENGINEERING/POLICY session, not a strategy experiment: no configs registered, no backtest
tuning, frozen champion v2 untouched. Output = `backtest/guardrails.py` (ops monitors + hard limits)
and this note.

## Case studies

### 1. LTCM (1998) — leverage + liquidity + model hubris
- Balance-sheet leverage >25:1, rising to ~130:1 as losses compounded; Russian default shocked
  spreads beyond historical model assumptions; crowded convergence trades could not be exited
  without moving prices. Fed-brokered rescue.
- Sources: Federal Reserve History essay (federalreservehistory.org/essays/ltcm-near-failure);
  President's Working Group report "Hedge Funds, Leverage, and the Lessons of LTCM"
  (home.treasury.gov/system/files/236/hedgfund.pdf); Craine (Berkeley) lecture notes;
  CLS Blue Sky Blog retrospective (2018).
- Lesson for the desk: models estimated on calm history understate tail correlation; leverage
  converts a survivable drawdown into ruin; liquidity of the instrument matters as much as the signal.

### 2. Victor Niederhoffer (1997) — negative convexity + revenge trading
- After Thai-baht losses, sold naked S&P puts to "make back" losses; 27 Oct 1997 -7% day wiped out
  ~$130M including cash reserves; margin call ended the fund. 20-year 30%-CAGR track record did not
  protect against one mis-sized short-vol position.
- Sources: Washington Post (17 Nov 1997) "Market's Crash Destroys Trader"; SteadyOptions case study
  "How Victor Niederhoffer Blew Up — Twice"; Macro Ops position-sizing analysis; FutureBlind
  "The Blow-Up Artist" (New Yorker synthesis).
- Lesson: never hold instruments with unbounded/convex downside; never size up to recover a loss;
  "the market has never done this before" is not a risk limit.

### 3. Quant Quake (Aug 6-10, 2007) — crowding + forced deleveraging
- A forced liquidation of one large factor portfolio cascaded through hundreds of funds holding
  densely overlapping positions; independently-managed funds became near-perfectly correlated in
  the unwind. Risk models fit on 2004-07 calm data contained no information about crowded-unwind
  tail correlation.
- Sources: Khandani & Lo, "What Happened to the Quants in August 2007?" (NBER WP 14465;
  Journal of Financial Markets 2011); MIT/Lo "The Quant Meltdown: August 2007"; CBS
  "Imitation and Liquidation" (2019).
- Lesson: when realized vol/correlation spikes abruptly, historical covariance is stale; a spike
  monitor should escalate reporting, not necessarily trade (v2's vol targeting already de-risks
  mechanically; E4/E8 showed reactive kill-switches hurt).

### 4. Amaranth (2006) — concentration
- ~$5B (half of AUM) lost in 3 weeks on concentrated calendar-spread natural-gas futures; single
  sector, single trade thesis, sized far beyond exit liquidity.
- Sources: Chincarini, "A Case Study on Risk Management: Lessons from the Collapse of Amaranth
  Advisors" (SSRN 1633589) and "Natural Gas Futures and Spread Position Risk" (SSRN 1086865);
  Senate PSI investigation record.
- Lesson: cap single-theme concentration; broad index exposure ≠ single-name/sector exposure.

### 5. Industry best practice (limits frameworks)
- CFTC/industry "Best Practices for the Hedge Fund Industry" (Managed Funds/PWG report,
  cftc.gov best-practices PDF); Hedge Fund Journal "Risk Practices in Hedge Funds"; Resonanz
  Capital manager-assessment checklist. Common core: written limits on position/sector/portfolio
  NAV-at-risk, drawdown escalation ladders, leverage caps, stress tests that shock vol, prices,
  and liquidation horizon.

## Codified guardrails (backtest/guardrails.py) — mapped to failures

| # | Guardrail | Hard limit | Failure it answers |
|---|---|---|---|
| G1 | Leverage cap | gross exposure ≤ 1.0 × NAV, no shorting, no margin | LTCM |
| G2 | Instrument whitelist | cache-universe ETFs/mega-caps only; NO derivatives, NO short-vol, NO unbounded-loss instruments | Niederhoffer |
| G3 | No revenge sizing | exposure changes only from the frozen champion's signal; never after a loss to "recover" | Niederhoffer |
| G4 | Concentration caps | single stock ≤ 20% NAV; single sector ETF ≤ 30%; broad-index ETFs exempt | Amaranth |
| G5 | Vol/corr spike monitor | 20d realized vol > 2× its 1y median, or |daily move| > 4σ → AMBER flag in next briefing | Quant Quake |
| G6 | Drawdown escalation ladder | -10% live: AMBER note; -15%: RED — dedicated review session; -20%: Phase criterion 3 breached — immediate report to Mr. Menéndez. REPORTING escalation only — no auto-liquidation (E4/E8 evidence: reactive kill-switches damage Sharpe without improving DD) | LTCM/all |
| G7 | Stale-data guard | stale_days > 4 → no marks presented as live; no rebalancing on stale signals | ops |

All guardrails are MONITORS and HARD CONSTRAINTS on operations; none alters the frozen champion's
signal. G1/G2/G4 are already satisfied by construction (v2 is long-only, cap 1.0, 100% SPY);
codifying them makes violation impossible to miss if a future champion changes the book.
