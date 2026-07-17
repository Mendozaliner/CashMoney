# Mean reversion (RSI-2, Bollinger, IBS) — research notes, session 11 (2026-07-17)

Last unexplored charter-queue family. Runs as a candidate NEW SLEEVE (the
frozen v2 live track is untouched; Phase-2 rules).

## Synthesis of sources

1. **Connors RSI(2)** (QuantifiedStrategies.com guide; Connors & Alvarez 2008,
   "Short Term Trading Strategies That Work"): buy S&P when 2-period RSI < 5/10
   with price above the 200d SMA; exit on strength (RSI > 65-70 or close > 5d MA).
   Claimed: ~9%/yr on SPY 1993→present while invested only ~28% of the time;
   win rates 65-75%; max DD ~34% in adverse periods. Connors found fixed
   stop-losses HURT (stops trigger right before the bounce).
2. **Skeptical prior — Price Action Lab (2018)**: formal tests suggest the
   RSI(2) edge is indistinguishable from random / a data-mining artifact once
   selection bias is accounted for. This desk's default expectation.
3. **Pagonidis, "The IBS Effect" (NAAIM Wagner 2013)**: IBS=(C-L)/(H-L).
   Next-day mean return +0.35% when IBS<0.2 vs -0.13% when IBS>0.8 across
   equity index ETFs. Later replications mixed (fails in some markets);
   commissions "greatly decrease returns and increase drawdowns".
4. **Bollinger mean reversion** (SSRN 5713082; Atlantis Press 125991306):
   lower-band entries/middle-band exits on index ETFs can look good in-sample;
   OOS evidence mixed and cost-sensitive.
5. **Edge decay** (Do & Faff 2010/2012 on pairs; Alvarez "MR vs TF through the
   years"): published mean-reversion edges decay post-publication; MR on
   S&P-class indexes weakened after ~2013.
6. **Costs** (MDPI Risks 14(4):84; QuantVero): short-horizon MR is exquisitely
   cost-sensitive; at retail-ish 0.15%/round-trip-leg assumptions, high-turnover
   variants lose most of the paper edge. SPY specifically: buy-and-hold's
   zero-friction advantage beat overnight/day-split strategies.
7. **Desk-internal prior evidence**: every un-gated fast signal tested here
   (E5 sector momo, E16 AAA) crashed in bears; the SMA200 gate is mandatory.
   High-VIX de-risking failed (E2) because panic precedes bounces — which cuts
   FOR buy-the-dip entries but the desk's EOD next-close fill handicaps 1-3
   day holds.

## Design decisions
- All three families long-only, binary, SMA200-gated, SPY only, 0.15% cost per
  side on traded notional, T-bill on idle cash. Engine fill: next close after
  signal (honest EOD handicap; no intraday fills).
- Max 2 tunable params each: RSI2 entry {5,10,15} x exit {70,80} (6 cfg);
  Bollinger k {2.0,2.5} x exit {mid, mid+0.5sd} (4 cfg); IBS entry {0.1,0.2}
  x exit {0.7,0.8} (4 cfg). 14 configs total, separately pre-registered.
- Success bar (pre-registered, per family): mean WF Sharpe >= 0.844 (v2's) AND
  worst-fold DD > -20% AND DSR >= 0.95 AND OOS diff-vs-SPY CI clears zero.
  Low avg exposure means CAGR will lag SPY badly; Sharpe-based bar is the
  fair test, terminal $ reported for honesty.
- Expectation: FAIL at the significance gate (skeptical prior #2, cost
  sensitivity #6, decay #5). Value of the session: closing the last
  unexplored charter family with a definitive, pre-registered answer.

## Sources
- https://www.quantifiedstrategies.com/rsi-2-strategy/
- https://www.priceactionlab.com/Blog/2018/08/rsi2-trading-strategy/
- https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5713082
- https://www.atlantis-press.com/article/125991306.pdf
- https://alvarezquanttrading.com/blog/mean-reversion-vs-trend-following-through-the-years/
- https://www.mdpi.com/2227-9091/14/4/84
- https://www.quantvero.com/algo-trading/mean-reversion-trading-strategy/
