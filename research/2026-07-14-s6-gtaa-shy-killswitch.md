# Research notes — s6 (2026-07-14): Faber GTAA, SHY-harbor Dual Momentum, conservative kill-switch

## 1. Faber GTAA (roadmap #1 — new sleeve candidate)
- Faber (2007, rev. 2013), "A Quantitative Approach to Tactical Asset Allocation"
  (SSRN 962461). Rule: each asset class held at a fixed slot weight iff price >
  10-month SMA at month-end; slot goes to T-bills otherwise. Claim: equity-like
  returns with "bond-like volatility and drawdown"; US-stocks timing cut MaxDD
  from ~46% to <10-20% depending on period. https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf
- Real-time tracking (Extrategic Dashboard; AllocateSmartly "Aggressive GTAA";
  PortfolioDB GTAA-13): live results "considerably less optimistic than the
  original paper" — clear OOS decay; expect the same and hold the DSR bar.
- Key structural improvement over failed E3 (Dual Momentum w/ TLT): NO forced
  bond-as-safe-haven. Each asset is gated on ITS OWN trend, so 2022 (stocks and
  bonds down together) sends both slots to T-bill cash instead of parking in a
  crashing TLT.
- Our adaptation to cache universe: SPY (US lg), IWM (US sm), IEF (7-10y UST),
  GLD (gold). GLD history starts 2004-11 → fold 1 is truncated (~2005-11 on)
  and MISSES the dot-com bust. Logged as an honest limitation of this sleeve.

## 2. Dual Momentum with SHY defensive (roadmap #2 — E3 retry)
- 2022 was the canonical failure year for GEM-style rotation into duration:
  classic dual-momentum variants lost 10-24% in 2022 because stocks AND bonds
  fell together (AGG -13%); the defensive asset itself crashed
  (bestfolio.app/blog/dual-momentum-2022-canary-models; allocatesmartly.com
  "Dynamic Bond Variations of 10 TAA Strategies").
- Standard fixes: (a) short-duration defensive (SHY/BIL) — smaller defensive
  DD, some CAGR give-up; (b) canary universes (Keller BAA/HAA — out of scope,
  needs intl data); (c) momentum-test the defensive asset itself, else cash.
- We test (a): identical GEM machinery as E3 but defensive = SHY. SHY starts
  2002-07 → fold 1 becomes ~2003-07→2009 (still contains 2008 — the fold that
  matters most for a defensive harbor).

## 3. Conservative kill-switch (roadmap #3 — E4 retry)
- E4 (s5) failed from whipsaw: kill at -12%/-15% sits INSIDE v2's normal DD
  range (worst fold -20.5%), so it fired on noise. City University working
  paper (SSRN 2126476, "Trend Following, Stop Losses and the Frequency of
  Trading") finds stop-loss value is highly parameter- and frequency-dependent
  and often negative net of costs; practitioner literature agrees whipsaw
  clusters are the main cost (quantifiedstrategies.com; abovethegreenline.com).
- Retry with the trigger BELOW the strategy's historical DD envelope: kill at
  -20% (fires only in GFC/COVID-class events), re-enter at -10%. 2 configs only.
- Skeptical prior: at -20% the switch almost never fires → expected verdict is
  "no measurable improvement, discard" — which would still be a useful negative
  (caps the roadmap item permanently).

## Sources
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461 (Faber GTAA)
- https://mebfaber.com/timing-model/ (updated data)
- https://allocatesmartly.com/aggressive-global-tactical-asset-allocation/
- https://portfoliodb.co/portfolios/global-tactical-asset-allocation-13-gtaa-13-meb-faber
- https://bestfolio.app/blog/dual-momentum-2022-canary-models
- https://allocatesmartly.com/dynamic-bond-variations-of-10-taa-strategies/
- https://openaccess.city.ac.uk/17842/8/BLACKBOX%20%20%20SSRN-id2126476.pdf (stop-loss frequency-of-trading)
- https://www.quantifiedstrategies.com/dual-momentum-trading-strategy/
