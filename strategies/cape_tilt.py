"""CAPE (Shiller P/E) value tilt on v2 champion (session 22, E31).

When the cyclically adjusted P/E ratio (CAPE) is in the upper tail of its
expanding-window percentile distribution, reduce v2 target exposure by a mild
tilt. The CAPE signal uses monthly Shiller data with a 1-month publication lag
to avoid lookahead; it is forward-filled to daily frequency.

Academic basis:
- Shiller (1981, 2000): CAPE is the best long-horizon return predictor for
  the S&P 500; R^2 rises from ~0 at 1 year to 40-50% at 10 years.
- Campbell & Shiller (1988) JF: earnings yield predicts returns at long
  horizons but NOT short horizons (1-year R^2 < 2%).
- Asness (2012) "An Old Friend": CAPE at top decile implies negative
  10-year forward equity risk premium but near-zero next-year signal.
- Siegel (2016): CAPE biased upward by post-1990 accounting changes; current
  readings overstate overvaluation relative to historical comparisons.

Skeptical prior: expect FAIL at 1-3 year horizons. CAPE ~41 (2026-07) is
top decile, but the same was true 2015-2020 when equities kept rallying.
The v2 vol-targeting overlay already reduces equity exposure in high-vol
drawdown environments, which often (not always) coincide with elevated CAPE.

Tunable parameters: cape_pct, tilt (both ≤2 per convention).
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_shiller

DEFAULTS = {"cape_pct": 0.90, "tilt": 0.25}


def signals(close: pd.Series,
            cape_pct: float = 0.90,
            tilt: float = 0.25,
            target_vol: float = 0.18,
            lookback: int = 20) -> pd.Series:
    """Return exposure signal with a mild CAPE top-decile tilt.

    When the expanding-window CAPE percentile rank (lagged 1 month for
    publication lag) exceeds `cape_pct`, the v2 exposure is multiplied by
    (1 - tilt). Below the threshold, exposure is unchanged.

    Args:
        close      : SPY daily adjusted close.
        cape_pct   : Expanding-window percentile threshold (0.90 = top 10%).
        tilt       : Fractional exposure reduction when CAPE is extreme.
        target_vol : V2 annualized vol target (fixed at champion 0.18).
        lookback   : V2 realized-vol lookback days (fixed at champion 20).
    """
    base = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    shiller = load_shiller()
    cape = shiller["CAPE"].dropna()

    # Expanding-window percentile rank; shift(1) = 1-month publication lag
    cape_rank = cape.expanding().rank(pct=True).shift(1)
    top_decile = (cape_rank >= cape_pct).astype(float)

    # Forward-fill monthly signal to daily, aligned on close dates
    cape_flag_daily = (
        top_decile
        .reindex(close.index, method="ffill")
        .fillna(0.0)
    )

    # Mild tilt: multiply v2 by (1 - tilt) when CAPE is extreme
    multiplier = 1.0 - tilt * cape_flag_daily
    return (base * multiplier).clip(0.0, 1.0)
