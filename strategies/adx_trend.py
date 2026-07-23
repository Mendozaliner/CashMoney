"""ADX Trend Strength Filter (session 18).

Philosophy: J. Welles Wilder (1978) — "New Concepts in Technical Trading Systems."
Wilder's Average Directional Index (ADX) measures the STRENGTH of a trend,
irrespective of its direction. The key insight distinguishing this from v2:

  - v2 (SMA200): "Is the market trending UP relative to its moving average?"
    → Direction-based entry
  - ADX: "Is the market trending at all — and is that trend STRONG ENOUGH?"
    → Strength-based filter, applied ON TOP of direction

Rationale for this combination (v2 + ADX):
  - v2 generates signals during both strong and weak trends
  - Whipsaws in v2 happen most often when the market oscillates without clear
    trend (ADX < 20 = choppy/ranging)
  - Only participating when trend is strong (ADX > threshold) avoids the
    costly whipsaw periods while maintaining exposure in sustained moves

ADX Construction (Wilder 1978):
  TR = max(H-L, |H-prevC|, |L-prevC|)
  +DM = (H - prevH) if (H - prevH) > (prevL - L) else 0
  -DM = (prevL - L) if (prevL - L) > (H - prevH) else 0
  ATR_n = EWM(TR, span=n)
  +DI_n = 100 * EWM(+DM, n) / ATR_n
  -DI_n = 100 * EWM(-DM, n) / ATR_n
  DX   = 100 * |+DI - -DI| / (+DI + -DI)
  ADX  = EWM(DX, span=n)

References:
  - Wilder, J.W. (1978). New Concepts in Technical Trading Systems.
  - Kaufman, P. (2013). Trading Systems and Methods. 5th ed.
  - Sewell, M. (2011). "Characterization of Financial Time Series."
    UCL Research Note. (ADX empirical properties in index markets)
"""
import numpy as np
import pandas as pd

from strategies import sma_trend

TRADING_DAYS = 252
DEFAULTS = {"adx_period": 14, "adx_threshold": 20, "target_vol": 0.18,
            "vol_lookback": 20}


def _adx(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """Compute ADX using Wilder's exponential smoothing."""
    ph = high.shift(1)
    pl = low.shift(1)
    pc = close.shift(1)

    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)

    # Directional movements
    up_move = high - ph
    dn_move = pl - low

    plus_dm  = np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0)

    plus_dm  = pd.Series(plus_dm, index=close.index, dtype=float)
    minus_dm = pd.Series(minus_dm, index=close.index, dtype=float)

    alpha = 1.0 / period
    atr     = tr.ewm(alpha=alpha, adjust=False).mean()
    plus_di  = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr

    di_sum  = (plus_di + minus_di).replace(0, np.nan)
    dx      = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx     = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx


def signals(close: pd.Series, adx_period: int = 14,
            adx_threshold: float = 20.0, target_vol: float = 0.18,
            vol_lookback: int = 20,
            high: pd.Series | None = None,
            low: pd.Series | None = None) -> pd.Series:
    """v2 trend direction × ADX trend-strength filter × vol targeting.

    When ADX < adx_threshold (choppy/ranging market), exposure = 0.
    When ADX >= adx_threshold AND v2 trend is ON, use vol-targeted exposure.

    If high/low are not provided, they are approximated from close using a
    small smoothing window (necessary for OHLCV-less contexts and tests).
    """
    if high is None:
        high = close.rolling(3, min_periods=1).max()
    if low is None:
        low = close.rolling(3, min_periods=1).min()

    adx = _adx(high, low, close, period=adx_period)

    trend_gate = sma_trend.signals(close, window=200, band=0.03)

    adx_on = (adx >= adx_threshold).astype(float)

    rv = close.pct_change().rolling(vol_lookback).std() * np.sqrt(TRADING_DAYS)
    scale = (target_vol / rv).clip(upper=1.0)

    return (trend_gate * adx_on * scale).fillna(0.0).clip(0.0, 1.0)
