# Research notes s21 — 2026-07-24 — Valuation (CAPE) as a timing overlay: literature pass

Purpose: roadmap #6 (value tilt) is the last open theory family, blocked on fundamentals
data. Before building the feed, survey the evidence so the eventual pre-registered
hypothesis is honest. Default expectation: FAIL — the literature is mostly negative on
CAPE as a *timing* signal.

## What the literature says

1. **Asness, "An Old Friend: The Stock Market's Shiller P/E" (AQR, 2012).**
   10-yr forward average real returns fall nearly monotonically as starting CAPE rises;
   the whole return distribution shifts left when expensive. BUT: this is a
   *decade-horizon expected-return* result, not a trade signal.
   https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/An-Old-Friend-The-Stock-Markets-Shiller-PE.pdf

2. **Asness, Ilmanen & Maloney, "Market Timing: Sin a Little" (AQR).**
   Pure contrarian value timing of one market is very hard; adding a momentum signal
   helps resolve the conflict; position changes should be modest ("sin a little").
   Directly relevant: any CAPE overlay on v2 should be a *mild* exposure tilt combined
   with the existing trend gate, never a standalone in/out switch.
   https://www.aqr.com/Insights/Research/Journal-Article/Market-Timing-Sin-a-Little

3. **Kitces: "Shiller PE: Bad Market Timing, Good Retirement Planning."**
   CAPE correlation with 1-yr returns ~ zero; valuable only for long-term planning
   assumptions. https://www.kitces.com/blog/shiller-cape-market-valuation-terrible-for-market-timing-but-valuable-for-long-term-retirement-planning/

4. **Advisor Perspectives, "Beware of the Misinterpretations of the CAPE Ratio."**
   Timing only paid, on average, in the extreme top of the CAPE distribution
   (upper half of 10th decile, CAPE > ~27.6 historically) — i.e., a rare-extremes
   signal, mostly inactive. https://www.advisorperspectives.com/articles/2018/04/02/beware-of-the-misinterpretations-of-the-cape-ratio

5. **Dimensional, "CAPE Fear."** No compelling evidence valuation indicators improve
   allocation decisions; cites the Jan-2018 negative-prediction episode followed by
   +11.75%/yr real over 3.5 years. https://www.dimensional.com/se-en/insights/cape-fear-should-investors-be-concerned-with-market-valuations

6. **Ma et al. / Idea Farm, "CAPE Ratios and Long-Term Returns" (2026 review) +
   Component CAPE research (FA-mag).** Reconstructed/component CAPE recovers strong
   10-yr OOS R² (~0.56) and higher certainty-equivalent returns in allocation sims —
   evidence the *long-horizon* signal is real even if short-horizon timing is not.
   https://theideafarm.com/wp-content/uploads/2026/01/20260112CAPE.pdf

7. **QuantPedia, "An Interesting Analysis of Shiller's CAPE Ratio."** Confirms
   decile-conditional analysis: only extreme deciles carry usable information.
   https://quantpedia.com/an-interesting-analysis-of-shillers-cape-ratio/

8. **Data source: Robert Shiller's monthly dataset** (price, dividends, earnings, CPI,
   CAPE back to 1871): ie_data.xls, canonical at econ.yale.edu, now also mirrored at
   shillerdata.com; datahub.io keeps a parsed CSV mirror. Current CAPE ≈ 41 (Jul 2026,
   GuruFocus) — top decile territory, which is exactly when the literature says the
   signal has *some* teeth.

## Implications for the eventual experiment (NOT registered yet — data first)

- Signal: CAPE percentile vs trailing history (expanding window, no lookahead — the
  percentile must be computed only from data available at each date).
- Form: mild exposure tilt on v2 (e.g., scale exposure 1.0 → 0.75 only when CAPE is
  in its top historical decile AND the trend gate is already marginal), never a
  standalone in/out. Max 2 parameters (percentile threshold, tilt size).
- Monthly data → signal changes ~monthly; turnover cost trivial.
- Expected outcome per literature: at best marginal; CI vs v2 will likely straddle
  zero (the overlay is inactive ~90% of the time). Registered bar must acknowledge
  this: the family earns at most a watch-list slot unless it clears the full gate.
- Prior sessions' lesson (E29/E30): overlays on signals v2 already encodes fail on
  correlation ~0.97. CAPE is one of the few signals NOT derivable from price/vol —
  orthogonality is the one reason this family is worth the alpha spend.

## Engineering done this session (zero configs)

`scripts/fetch_data.py` extended with a Shiller monthly fundamentals fetcher
(yale ie_data.xls primary, datahub CSV fallback) writing
`data/cache/fundamentals/shiller_monthly.csv`; `data.loader.load_shiller()` added;
parser unit-tested offline. First real file lands with the next weekday Action run.
