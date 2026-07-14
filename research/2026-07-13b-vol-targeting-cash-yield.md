# Research notes — 2026-07-13 session 2: cash yield while flat + volatility targeting

## Question
Roadmap #2 and #3: (a) does crediting T-bill yield on flat periods improve the
champion (SMA200/b3 long/flat on SPY-proxy)? (b) does a volatility-targeting
overlay (scale exposure to a vol target, capped at 1.0) improve OOS Sharpe
without worsening MaxDD?

## Sources (synthesis)
1. Moreira & Muir (2017), "Volatility-Managed Portfolios", J. Finance.
   Scaling exposure by inverse of prior-month realized variance raises Sharpe:
   variance shocks raise future variance much more than future expected return.
   https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf
2. Cederburg, O'Doherty, Wang & Yan (2020), "On the performance of
   volatility-managed portfolios", JFE 138(1). Real-time (out-of-sample)
   implementations generally FAIL to beat unmanaged portfolios; spanning-
   regression evidence is not implementable. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3357038
3. Barroso & Detzel (2021), "Do limits to arbitrage explain the benefits of
   volatility-managed portfolios?" — vol management largely does not survive
   transaction costs. (Via Cederburg et al. discussion.)
4. Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018), "The
   Impact of Volatility Targeting", JPM 45(1). Across 60 assets: Sharpe
   improvement holds for RISK assets (equities, credit) via leverage effect;
   main benefit is taming left tails — vol-targeted portfolios are small when
   crashes hit. https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf
5. Bongaerts, Kang & van Dijk (2020), "Conditional Volatility Targeting", FAJ
   76(4). Unconditional vol targeting = high turnover, inconsistent net gains;
   adjusting exposure ONLY in extreme-vol states preserves benefit at a
   fraction of the turnover. https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853
6. Faber (2007), "A Quantitative Approach to Tactical Asset Allocation" —
   the cash leg earns 90-day T-bills, a material chunk of the timing model's
   long-run return. https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf
7. Allocate Smartly, "Meb Faber's Tactical Yield" — practitioner confirmation
   that cash-leg yield materially affects timing-model results.
   https://allocatesmartly.com/meb-fabers-tactical-yield-simple-and-intuitive/

## Design decisions driven by the literature
- Vol overlay is gated by the existing trend filter (exposure = trend × vol
  scale, cap 1.0): Harvey et al. benefit concentrates in risk assets; cap
  avoids leverage; gating keeps turnover down (Bongaerts et al. warning).
- Costs 0.1% per unit of traded notional — Cederburg/Barroso-Detzel say net-of-
  cost is where vol management dies, so evaluation is net.
- Cash sleeve at T-bill yield tested as its own experiment (E1) so the rf
  effect is not conflated with the vol effect (E2); E3 = both.
- Skeptical prior: expect E2 to be marginal OOS (Cederburg et al.); the
  keep/revert bar stays: OOS Sharpe > champion AND MaxDD not >10% worse rel.

## Multi-asset pipeline attempt (roadmap #1, bounded)
- github.com/datasets/finance-vix: daily VIX OHLC 1990 -> 2026-07-10. ACQUIRED,
  committed to data/cache/vix_daily.csv. Unblocks VIX regime filter (roadmap #5).
- GitHub search API blocked by sandbox; no ETF/Mag-7 OHLCV repo found among
  known candidates (US-Stock-Symbols = symbols only; upstream us-market-data
  repo carries only SPY-proxy + LIBOR). DIA/QQQ/Mag-7 benchmarks remain blocked.
