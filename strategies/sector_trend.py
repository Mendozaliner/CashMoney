"""Sector Momentum with Per-Sector Trend Gate (roadmap item #4, retry of E5).

Philosophy: Cross-sectional sector momentum (E5, s5) failed because of the
2000-09 dot-com bubble: XLK (Technology) dominated the momentum rankings
entering the bubble top, producing a -51.8% MaxDD. The root cause was pure
momentum with no protection against entering sectors in structural decline.

This strategy adds a per-sector SMA200 trend gate before momentum ranking:
a sector must be ABOVE its own 200-day SMA to be ELIGIBLE for selection.
This gates out sectors in downtrends — exactly what would have blocked XLK
in 2000-01 when it was below its own moving average as the bubble burst.

The combined momentum + trend filter is grounded in the same research that
underlies v2: trend filters (Faber 2007, Zakamulin 2014/2018) identify
structural regimes; momentum (Moskowitz & Grinblatt 1999) ranks within them.
The insight: strong momentum in a sector below its trend is a warning sign,
not a buy signal. Both filters must agree before taking a position.

Rule:
  1. Compute lookback-21d momentum for all available sector ETFs.
  2. Per-sector trend gate: mark sector ELIGIBLE only if Close > SMA(200).
     Sectors below their SMA200 are excluded (momentum set to NaN for ranking).
  3. Rank eligible sectors. Select top_n by momentum among eligibles.
  4. Equal-weight allocation to top_n eligible sectors; rest in cash.
  5. If fewer than min_eligible sectors pass the trend gate, stay fully in cash.

Research basis:
- Moskowitz & Grinblatt (1999). "Do Industries Explain Momentum?" J. Finance 54(4).
  Industry momentum significant after FF adjustment; ~6%/yr excess.
- Asness, C. et al. (2013). "Value and Momentum Everywhere." J. Finance 68(3).
  Momentum pervasive across industries, countries, asset classes.
- O'Shaughnessy (2012). "What Works on Wall Street." Top-decile relative
  strength strategies historically best performers among fundamentals screens.
- Faber (2007) / Zakamulin (2014): SMA200 trend gate reduces drawdown and
  filters regime-change risk — the same basis as v2's trend filter.
- Novy-Marx (2012): sector momentum partially explained by value signals.
  The trend gate partially addresses this by requiring price confirmation.
- E5 failure post-mortem: momentum rankings entering 2000 were XLK-dominated
  with no regard for trend state. XLK's SMA200 was violated by early 2001;
  this gate would have prevented entry and limited the -51.8% DD.
- Skeptical prior: Barroso & Santa-Clara (2015) crash risk; but per-sector
  gating reduces position concentration in overextended sectors. Pre-registered
  success bar requires DSR >= 0.95 AND diff-vs-SPY CI clears zero.

Universe: S&P 500 SPDR sector ETFs (all have history to 1998-1999):
  XLK (Tech), XLF (Financials), XLE (Energy), XLV (Healthcare), XLY (Cons. Disc.)
  XLP (Cons. Staples), XLI (Industrials), XLU (Utilities), XLB (Materials)
  XLRE (Real Estate, 2015+), XLC (Comm. Services, 2018+)

Interface: multi_signals(price_panel, lookback, top_n) -> pd.DataFrame (weights).
Parameters (max 2): lookback (momentum window, days), top_n (sectors to hold).
"""
import pandas as pd
import numpy as np

SECTOR_TICKERS = [
    "XLK", "XLF", "XLE", "XLV", "XLY",
    "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC",
]
SKIP_DAYS = 21
TREND_WINDOW = 200
MIN_ELIGIBLE = 2

DEFAULTS = {"lookback": 252, "top_n": 3}


def multi_signals(price_panel: pd.DataFrame, lookback: int = 252,
                  top_n: int = 3) -> pd.DataFrame:
    """Weight DataFrame for sector momentum gated by per-sector SMA200 trend.

    Only sectors above their own 200-day SMA are eligible for momentum selection.
    Equal-weight allocation among selected sectors; rest in cash.
    At least min_eligible sectors must pass the trend gate to generate a signal.
    """
    available = [t for t in SECTOR_TICKERS if t in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)

    if len(available) < MIN_ELIGIBLE:
        return weights

    px = price_panel[available]
    sma200 = px.rolling(TREND_WINDOW).mean()
    above_trend = px.gt(sma200) & sma200.notna()

    window = max(lookback - SKIP_DAYS, 1)
    mom = px.pct_change(window).shift(SKIP_DAYS)

    # Apply trend gate: sectors below SMA200 are ineligible (NaN for ranking)
    mom_gated = mom.where(above_trend, other=float("nan"))

    # Eligible = has valid gated momentum (above trend AND sufficient history)
    n_eligible = mom_gated.notna().sum(axis=1)
    enough = n_eligible >= MIN_ELIGIBLE

    # Rank eligible sectors only (NaN sectors go to last place)
    ranks = mom_gated.rank(axis=1, ascending=False, na_option="bottom")

    eff_top = n_eligible.clip(upper=top_n)

    for ticker in available:
        in_top = (ranks[ticker] <= top_n) & mom_gated[ticker].notna()
        weights.loc[enough & in_top, ticker] = (
            1.0 / eff_top.loc[enough & in_top]
        )

    return weights
