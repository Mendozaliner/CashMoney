"""CAPE-tilt overlay on the frozen v2 vol-target champion (E31).

Shiller's CAPE (Cyclically Adjusted P/E) predicts 10-year real equity returns
but has near-zero short-horizon (1-2y) predictive power. This strategy applies
a MILD downside tilt to v2's exposure only when CAPE is at historical extremes
(top-decile expanding-window percentile), then relies on the trend filter to do
the actual market timing.

Research basis:
- Shiller (2015) Irrational Exuberance: CAPE predicts 10yr returns, p10=10yr
  forward real return correlation ~0.60.
- Asness, Ilmanen, Maloney & Israel (2017) AQR: CAPE is real but slow —
  "one should expect to wait a decade, not a year, for mean reversion."
- Campbell & Shiller (1988) J.Finance: original publication.
- Straehl & Ibbotson (2017) FAJ: aggregate earnings yield forecasts equity RP.
- Graham & Dodd (1934): classic value investing foundation.
- Siegel (2016) critique: CAPE may be structurally elevated post-GAAP changes,
  making direct historical comparison hazardous (the case for mild, not binary,
  tilting).

Skeptical prior (per s21 literature pass):
- CAPE has been 'high' since the 1990s; a binary off-switch at the 90th
  percentile would have exited in 1997 and never returned.
- Statistically significant ONLY at decade horizons, not the 1-year horizon
  that matters for live portfolio management.
- Mild tilt (≤2 params, ≤12 configs) is the only defensible form.

No lookahead contract:
- CAPE index is shifted 1 month for publication lag.
- Percentile rank uses only data available up to each point (expanding window).
"""

import pandas as pd
import numpy as np

from strategies import vol_target
from data import loader

TRADING_DAYS = 252


def signals(
    close: pd.Series,
    target_vol: float = 0.18,
    lookback: int = 20,
    tilt_lo: float = 0.70,
    threshold_hi: float = 0.90,
) -> pd.Series:
    """Return fractional exposure in [0, 1] with CAPE tilt applied to v2.

    Parameters
    ----------
    tilt_lo : float
        Scale multiplier applied when CAPE >= threshold_hi percentile.
        e.g. 0.70 = reduce v2 exposure by 30% at extreme valuations.
    threshold_hi : float
        Expanding-window CAPE percentile that triggers the tilt.
        Default 0.90 = top decile of the full historical distribution.
    """
    base = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    try:
        shiller = loader.load_shiller()
    except FileNotFoundError:
        return base

    if "CAPE" not in shiller.columns:
        return base

    cape = shiller["CAPE"].dropna()
    if len(cape) < 120:
        return base

    # Shift 1 month for publication lag (CAPE data arrives with delay)
    cape_lagged = cape.shift(1).dropna()

    # Expanding-window percentile rank (no lookahead: rank uses only past values)
    pct = cape_lagged.expanding(min_periods=120).rank(pct=True)

    # Forward-fill monthly signal to daily frequency
    pct_daily = pct.reindex(close.index, method="ffill")

    # Scale multiplier: tilt down at top-decile CAPE, pass-through otherwise
    mult = pd.Series(1.0, index=close.index)
    mult[pct_daily >= threshold_hi] = tilt_lo

    return (base * mult).clip(0.0, 1.0)
