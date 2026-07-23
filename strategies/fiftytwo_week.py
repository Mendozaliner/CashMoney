"""52-Week High Proximity Momentum (session 18).

Philosophy: George & Hwang (2004) behavioral finance — anchoring effect.
Investors anchor their reference point for a stock/index to its 52-week high.
When price is near the 52-week high, institutional investors who delayed
buying "at the top" finally act, creating a self-reinforcing momentum effect.
When price is far below its 52-week high, uncertainty is high and selling
pressure dominates.

Signal: ratio = close / close.rolling(252).max()
  - If ratio >= thresh_high: maximum vol-targeted exposure (1.0 scaled)
  - If ratio <= thresh_low:  zero exposure (same as v2 risk-off)
  - Between thresh_low and thresh_high: linearly interpolated exposure

This differs fundamentally from v2:
  - v2: price vs. a trailing mean (level signal — "is market above average?")
  - 52wk: price vs. its best recent level (anchor signal — "is market near peak?")

References:
  - George, T.J. & Hwang, C. (2004). "The 52-Week High and Momentum Investing."
    Journal of Finance, 59(5), 2145–2176.
  - Hong, H. & Stein, J.C. (1999). "A Unified Theory of Underreaction,
    Momentum Trading, and Overreaction in Asset Markets." JF 54(6).
  - Jegadeesh, N. & Titman, S. (2001). "Profitability of Momentum Strategies:
    An Evaluation of Alternative Explanations." JF 56(2).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
DEFAULTS = {"thresh_high": 0.90, "thresh_low": 0.80, "target_vol": 0.18,
            "lookback_52wk": 252, "vol_lookback": 20}


def signals(close: pd.Series, thresh_high: float = 0.90,
            thresh_low: float = 0.80, target_vol: float = 0.18,
            lookback_52wk: int = 252, vol_lookback: int = 20) -> pd.Series:
    """52-week high proximity exposure with vol targeting.

    The 52-week rolling maximum uses shift(1) to avoid look-ahead.
    Linear interpolation between thresh_low (0 exposure) and thresh_high
    (maximum vol-targeted exposure).
    """
    peak_52 = close.shift(1).rolling(lookback_52wk, min_periods=lookback_52wk // 2).max()
    ratio = close / peak_52

    raw = ((ratio - thresh_low) / (thresh_high - thresh_low)).clip(0.0, 1.0)
    raw = raw.fillna(0.0)

    rv = close.pct_change().rolling(vol_lookback).std() * np.sqrt(TRADING_DAYS)
    scale = (target_vol / rv).clip(upper=1.0)

    return (raw * scale).fillna(0.0).clip(0.0, 1.0)
