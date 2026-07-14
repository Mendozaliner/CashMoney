"""Cross-sectional sector momentum strategy (session 5).

Philosophy: Buy the strongest sectors, avoid the weakest. Sector momentum
exploits the finding that sectors trending up over an intermediate lookback
(12-1 months) continue outperforming for the next 1-3 months on average.
Differs from dual_momentum.py (which is time-series / absolute momentum on
broad indices); this is purely cross-sectional rank-based selection.

Universe: S&P 500 SPDR sector ETFs (XLK, XLF, XLE, XLV, XLY, XLP, XLI,
XLU, XLB; plus XLRE/XLC when available — 2015/2018 inception). Sectors
with insufficient history are skipped gracefully each period.

Rule:
  1. Compute lookback-21d momentum for each available sector.
  2. Rank sectors. Select top_n by momentum rank.
  3. Equal-weight allocation to the selected sectors; rest in cash.
  Monthly signal, computed daily for continuous update.

Research basis:
- Moskowitz & Grinblatt (1999). "Do Industries Explain Momentum?"
  J. Finance 54(4). Industry/sector momentum significant after controlling
  for individual-stock momentum; FF-adjusted alpha ~6% annualized.
- O'Shaughnessy (2012). "What Works on Wall Street" (4th ed.). Sector
  relative strength strategies among the top-decile performers historically.
- Asness et al. (2013). "Value and Momentum Everywhere." J. Finance 68(3).
  Momentum pervasive across industries, countries, asset classes.
- Sectorspdr.com backtests (1998–): sector rotation strategies typically
  outperform SPY on raw return with higher volatility.
- Skeptical prior: Novy-Marx (2012) sector momentum partially explained by
  industry-level value; real edge after costs uncertain. Pre-registered bar
  requires statistical significance AND deflated-Sharpe hurdle.

Interface: multi_signals(price_panel, lookback, top_n) -> pd.DataFrame.
Parameters (max 2): lookback (momentum window, days), top_n (sectors to hold).
"""
import pandas as pd
import numpy as np

SECTOR_TICKERS = [
    "XLK", "XLF", "XLE", "XLV", "XLY",
    "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC",
]
SKIP_DAYS = 21        # house-fixed 1-month skip (not a tunable param)
MIN_VALID_SECTORS = 4  # need at least this many sectors to generate a signal

DEFAULTS = {"lookback": 252, "top_n": 3}


def multi_signals(price_panel: pd.DataFrame, lookback: int = 252,
                  top_n: int = 3) -> pd.DataFrame:
    """Return a weight DataFrame (date × sector) for cross-sectional momentum.

    Sectors not in price_panel, or with < lookback days of history, receive
    zero weight. When fewer than MIN_VALID_SECTORS are available the row is
    all-zero (stay in cash for that period).
    """
    available = [t for t in SECTOR_TICKERS if t in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)

    if len(available) < MIN_VALID_SECTORS:
        return weights

    window = max(lookback - SKIP_DAYS, 1)
    mom = price_panel[available].pct_change(window).shift(SKIP_DAYS)

    # Number of sectors with valid momentum each day
    n_valid = mom[available].notna().sum(axis=1)
    enough = n_valid >= MIN_VALID_SECTORS

    # Rank: 1 = best; na_option='bottom' sends NaN sectors to the end
    ranks = mom[available].rank(axis=1, ascending=False, na_option="bottom")

    # Effective top_n: can't exceed the number of valid sectors
    eff_top = n_valid.clip(upper=top_n)

    for ticker in available:
        # In top_n when rank <= top_n AND sector has valid momentum
        in_top = (ranks[ticker] <= top_n) & mom[ticker].notna()
        weights.loc[enough & in_top, ticker] = (
            1.0 / eff_top.loc[enough & in_top]
        )

    return weights
