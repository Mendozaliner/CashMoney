"""Blended multi-lookback time-series momentum — Session 9, 2026-07-16.

Philosophy: traditional dual-momentum uses a single lookback (e.g. 12 months),
which produces a single regime-specific signal. Blending signals at multiple
lookbacks (1, 3, 6, 12 months) makes the position less sensitive to the exact
lookback and reduces momentum crashes: the full-invested state requires
agreement across ALL horizons, not just one.

Specifically, each lookback produces a normalized momentum score, and the
composite signal is their average. Combined with the proven SMA200/band trend
gate and vol-targeting from champion v2, the hypothesis is that this blended
signal is smoother (less whipsaw) than a single lookback without sacrificing
the trend-following edge.

This is distinct from all prior experiments:
- E3/E7 (Dual Momentum): single 12-month lookback, forced allocation to bonds
- v2 champion: SMA200 trend gate, no return-based momentum comparison
- E5/E11 (Sector momentum): cross-sectional, not time-series
- No harbor asset needed: de-risks to cash (not bonds, which failed in 2022)

Research basis:
- Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere", JF.
- AQR (Babu, Levine et al. 2020) "Trends Everywhere": multi-lookback averages.
- Hurst, Ooi & Pedersen (2017) "A Century of Evidence on Trend-Following".
- Baz et al. (2015, Deutsche Bank): 1/3/12mo TSMOM blend reduces crash risk.

Parameters (max 2):
  lookbacks : tuple of lookback months to blend (default (1,3,6,12))
  target_vol: annualized vol target for the vol-scaling layer (default 0.18)
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
DEFAULTS = {"target_vol": 0.18, "n_lookbacks": 4}  # n_lookbacks selects preset
SMA_WINDOW = 200
SMA_BAND = 0.03

# Preset lookback sets indexed by n_lookbacks param (2=short, 4=full, 3=mid)
LOOKBACK_SETS = {
    2: (63, 252),           # 3-month and 12-month
    3: (63, 126, 252),      # 3, 6, 12-month
    4: (21, 63, 126, 252),  # 1, 3, 6, 12-month
}


def signals(close: pd.Series, target_vol: float = 0.18,
            n_lookbacks: int = 4) -> pd.Series:
    """Time-series momentum: average of signals at multiple lookbacks.

    Each lookback L produces a binary signal: 1 if close > close.shift(L),
    else 0 (no short-selling). The composite is the average, so it ranges
    [0, 1] — 0 = ALL lookbacks are negative, 1 = ALL are positive, with
    intermediate values when lookbacks disagree.

    This composite momentum is gated by the SMA200/3% band trend filter and
    scaled by the vol-targeting layer (same as v2), so the signal is:
        composite_momentum × trend_gate × min(1, target_vol / realized_vol)
    """
    lbs = LOOKBACK_SETS.get(int(n_lookbacks), LOOKBACK_SETS[4])

    # Individual momentum signals (binary: above/below lagged close)
    mom_scores = []
    for lb in lbs:
        shifted = close.shift(lb)
        score = (close > shifted).astype(float)
        mom_scores.append(score)

    composite = pd.concat(mom_scores, axis=1).mean(axis=1)

    # SMA200/3%-band trend gate (same as champion)
    sma = close.rolling(SMA_WINDOW).mean()
    trend = (close > sma * (1.0 + SMA_BAND)).astype(float)
    trend = trend.where(sma.notna(), 0.0)

    # Vol-targeting scale (same as v2)
    rv = close.pct_change().rolling(20).std() * np.sqrt(TRADING_DAYS)
    scale = (target_vol / rv).clip(upper=1.0)

    result = (composite * trend * scale).fillna(0.0).clip(0.0, 1.0)
    return result
