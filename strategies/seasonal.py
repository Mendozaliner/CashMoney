"""Seasonal / Halloween-Effect overlay on the champion trend filter (session 12).

Philosophy: Academic literature documents a strong "sell in May" (Halloween)
effect -- equity returns are concentrated in the November-April half-year.
Overlaying a seasonal gate on v2's trend signal could reduce drawdown from
summer bear markets while retaining the winter bull market upside.

Rule:
    trend = v2 vol-targeted signal (SMA200/3% gate + vol scaling at 0.18)
    if month in good_months: exposure = trend (full signal)
    else:                     exposure = trend * off_season_scale

    Final exposure clipped to [0, 1].

Academic basis:
- Bouman & Jacobsen (2002) AER -- "The Halloween Indicator: Sell in May
  and Go Away" -- originally documented for 36 countries 1970-1998;
  since extensively replicated, including post-publication (Andrade et al.
  2013, Jacobsen & Zhang 2014).
- Haggard & Witte (2010) -- effect is robust net of transactions costs in
  the US and 36 other markets 1998-2008.
- Kamstra et al. (2003) AER -- seasonal affective disorder (SAD) mechanism:
  autumn depression -> risk aversion -> higher risk premia in winter.
- Skeptical prior: data-mined over-fitting risk; holding period is
  coarse (6-month blocks); has worked less well in recent decades (2010+
  US bull market ran through summer frequently).

Tunable parameters: good_months (tuple), off_season_scale (float 0..1).
Trend gate fixed at v2 champion (SMA200/3%, vol_target=0.18, lookback=20).
"""
import numpy as np
import pandas as pd

from strategies import vol_target as _vt


def signals(close: pd.Series,
            good_months: tuple = (11, 12, 1, 2, 3, 4),
            off_season_scale: float = 0.0,
            sma_window: int = 200,
            band: float = 0.03,
            vol_tgt: float = 0.18,
            lookback: int = 20) -> pd.Series:
    """Seasonal-gated vol-targeted trend exposure on a single close series.

    Args:
        close           : Adjusted close prices (pandas Series with DatetimeIndex).
        good_months     : Month numbers (1-12) with FULL signal; others scaled.
        off_season_scale: Fraction of trend signal applied in non-good months.
                          0.0 = fully flat in bad months; 0.5 = half exposure.
        sma_window      : SMA lookback (bars); fixed at 200 per champion.
        band            : Hysteresis band; fixed at 0.03 per champion.
        vol_tgt         : Vol target; fixed at 0.18 per champion.
        lookback        : Vol lookback (bars); fixed at 20 per champion.
    Returns:
        exposure : Series in [0, 1] aligned with close.index.
    """
    from strategies.sma_trend import signals as _sma
    rv = close.pct_change().rolling(lookback).std() * np.sqrt(252)
    trend = _sma(close, window=sma_window, band=band)
    scale = (vol_tgt / rv).clip(upper=1.0).fillna(0.0)
    base = (trend * scale).fillna(0.0).clip(0.0, 1.0)

    in_good = close.index.month.isin(good_months)
    seasonal_mult = pd.Series(
        np.where(in_good, 1.0, off_season_scale),
        index=close.index, dtype=float
    )
    return (base * seasonal_mult).clip(0.0, 1.0)
