"""Donchian Channel Breakout with volatility targeting (session 18).

Philosophy: Richard Dennis & William Eckhardt "Turtle Trading" (1983).
Breakout trend-following: go long when price exceeds the N-day highest high
(a new price channel breakout), exit when price falls below the M-day lowest
low. This is mechanically different from the SMA200 gate in v2:
  - v2: price LEVEL vs. a lagged moving average (mean-reversion anchor)
  - Donchian: price HIGH vs. RECENT RANGE (momentum breakout anchor)

Two classic systems from the original turtle rules:
  System 1: 20-day entry, 10-day exit (shorter, more frequent trades)
  System 2: 55-day entry, 20-day exit (longer, fewer trades)

Position sizing: vol-targeting overlay applied post-signal (same as v2).

References:
  - Covel, M. (2007). The Complete Turtle Trader.
  - Greyserman, A. & Kaminski, K. (2014). Trend Following with Managed Futures.
  - Abraham, Fazal & Rowenhorst (2002). "International Momentum and Time-Series
    Predictability", J. Portfolio Management.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
DEFAULTS = {"entry_window": 20, "exit_window": 10, "target_vol": 0.18,
            "vol_lookback": 20}


def signals(close: pd.Series, entry_window: int = 20, exit_window: int = 10,
            target_vol: float = 0.18, vol_lookback: int = 20) -> pd.Series:
    """Donchian channel breakout with vol-targeting position size.

    Entry: close > highest close of prior entry_window bars (breakout).
    Exit:  close < lowest close of prior exit_window bars.
    Position size: min(1, target_vol / realized_vol) applied when in-trend.
    """
    highest = close.shift(1).rolling(entry_window).max()
    lowest  = close.shift(1).rolling(exit_window).min()

    raw = pd.Series(np.nan, index=close.index, dtype=float)
    in_trade = False
    raw_vals = []

    for i in range(len(close)):
        h = highest.iloc[i]
        lo = lowest.iloc[i]
        c = close.iloc[i]

        if np.isnan(h) or np.isnan(lo):
            raw_vals.append(np.nan)
            continue

        if not in_trade:
            if c > h:
                in_trade = True
        else:
            if c < lo:
                in_trade = False

        raw_vals.append(1.0 if in_trade else 0.0)

    trend = pd.Series(raw_vals, index=close.index, dtype=float)

    rv = close.pct_change().rolling(vol_lookback).std() * np.sqrt(TRADING_DAYS)
    scale = (target_vol / rv).clip(upper=1.0)
    return (trend * scale).fillna(0.0).clip(0.0, 1.0)
