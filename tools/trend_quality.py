"""Trend Quality Filter — variance-ratio / Hurst-based trend detection.

Motivation
----------
The SMA200 trend filter in the champion CRQS strategy generates signals regardless
of whether the underlying price process is actually trending. In choppy, range-bound
markets (low autocorrelation) it produces whipsaw trades that degrade returns.

This module implements two complementary trend-quality metrics:

1. **Variance Ratio (VR)** — Lo & MacKinlay (1988).
   VR(q) = Var[r_t + r_{t-1} + ... + r_{t-q+1}] / (q × Var[r_t])
   over a rolling `window`. VR > 1 → positive autocorrelation (trending).
   VR < 1 → negative autocorrelation (mean-reverting / choppy).

2. **Hurst Exponent (H)** — Hurst (1951), rescaled-range method.
   H > 0.5 → persistent/trending; H = 0.5 → random walk; H < 0.5 → anti-persistent.
   Estimated via the log-log slope of R/S statistics over sub-periods within
   the rolling window.

These metrics let the CRQS strategy throttle back equity exposure when the market
is choppy, reducing whipsaw losses without missing genuine trends.

References
----------
Lo, A.W., MacKinlay, A.C. (1988). "Stock Market Prices Do Not Follow Random Walks:
  Evidence from a Simple Specification Test". The Review of Financial Studies, 1(1), 41–66.
Hurst, H.E. (1951). "Long-Term Storage Capacity of Reservoirs". Transactions of the
  American Society of Civil Engineers, 116, 770–808.
Peters, E.E. (1991). "Chaos and Order in Capital Markets". Wiley.
Chan, E.P. (2013). "Algorithmic Trading: Winning Strategies and Their Rationale".
  Wiley, ch. 3 (variance ratio as trend quality).
Korajczyk, R., Sadka, R. (2008). "Pricing the Commonality Across Alternative Measures
  of Liquidity". Journal of Financial Economics, 87(1), 45–72.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# Variance Ratio
# ---------------------------------------------------------------------------

def variance_ratio(returns: pd.Series, q: int = 20,
                   window: int = 63) -> pd.Series:
    """Rolling variance ratio VR(q) over `window` days.

    Parameters
    ----------
    returns : daily return series (close-to-close pct_change).
    q       : aggregation horizon in days (e.g., 10, 20, 40).
    window  : rolling estimation window in trading days.

    Returns
    -------
    pd.Series of VR(q) values; NaN for the first `window + q - 1` bars.

    Interpretation: VR > 1.0 → trending; VR < 1.0 → mean-reverting.
    """
    r = returns.copy()

    # q-day overlapping returns (rolling sum)
    q_ret = r.rolling(q).sum()

    # Rolling variance of 1-day returns and q-day returns
    var1 = r.rolling(window).var(ddof=1)
    varq = q_ret.rolling(window).var(ddof=1)

    vr = varq / (q * var1)
    return vr.rename("VR")


def variance_ratio_signal(returns: pd.Series, q: int = 20,
                          window: int = 63,
                          tqf_scale: float = 0.50) -> pd.Series:
    """Binary trend-quality multiplier in [tqf_scale, 1.0].

    Returns 1.0 when VR(q) > 1.0 (trending market),
    returns tqf_scale when VR(q) <= 1.0 (choppy / mean-reverting market).

    The multiplier is computed at bar t and applied with a 1-bar lag
    (shift(1)) to avoid lookahead — consistent with CRQS signal pipeline.

    Parameters
    ----------
    returns   : daily return series.
    q         : variance ratio aggregation horizon.
    window    : rolling estimation window.
    tqf_scale : equity multiplier in non-trending regimes (0 < tqf_scale < 1).

    Returns
    -------
    pd.Series of multipliers in [tqf_scale, 1.0], shifted by 1 day.
    """
    vr = variance_ratio(returns, q=q, window=window)
    # Trend regime: VR > 1.0 (positive autocorrelation)
    trending = (vr > 1.0)
    mult = trending.astype(float) + (~trending).astype(float) * tqf_scale
    # Fill NaN periods (warm-up) with 1.0 (no penalty during burn-in)
    mult = mult.fillna(1.0)
    # 1-bar lag so today's multiplier uses yesterday's VR
    return mult.shift(1).fillna(1.0).rename("TQF")


# ---------------------------------------------------------------------------
# Hurst Exponent (rescaled-range estimate)
# ---------------------------------------------------------------------------

def _hurst_rs(r: np.ndarray) -> float:
    """Hurst exponent via rescaled range over one window.

    Uses log-log slope of R/S at multiple sub-window lengths.
    Returns NaN if computation fails.
    """
    n = len(r)
    if n < 20:
        return np.nan
    # Sub-window sizes: powers of 2 up to n//2
    sizes = [s for s in [8, 16, 32, 64, 128, 256, 512] if s <= n // 2]
    if len(sizes) < 2:
        return np.nan

    rs_vals = []
    for size in sizes:
        chunks = n // size
        if chunks < 1:
            continue
        rs_chunk = []
        for i in range(chunks):
            seg = r[i * size: (i + 1) * size]
            mean_seg = seg.mean()
            dev = (seg - mean_seg).cumsum()
            r_range = dev.max() - dev.min()
            s = seg.std(ddof=1)
            if s > 0:
                rs_chunk.append(r_range / s)
        if rs_chunk:
            rs_vals.append((size, np.mean(rs_chunk)))

    if len(rs_vals) < 2:
        return np.nan

    log_sizes = np.log([s for s, _ in rs_vals])
    log_rs = np.log([rs for _, rs in rs_vals])
    # Hurst = slope of log(R/S) vs log(n)
    coeffs = np.polyfit(log_sizes, log_rs, 1)
    return float(coeffs[0])


def rolling_hurst(returns: pd.Series, window: int = 252) -> pd.Series:
    """Rolling Hurst exponent over `window` days.

    Computationally heavier than variance_ratio; use a longer window (≥252)
    for stable estimates. For backtesting, window=252 is the minimum
    recommended (Meilhac & Jostova, 2002).

    Returns
    -------
    pd.Series of H values in approximately [0, 1]; NaN during burn-in.
    H > 0.5 → trending; H ≈ 0.5 → random walk; H < 0.5 → mean-reverting.
    """
    r = returns.to_numpy()
    result = np.full(len(r), np.nan)
    for i in range(window - 1, len(r)):
        result[i] = _hurst_rs(r[i - window + 1: i + 1])
    return pd.Series(result, index=returns.index, name="Hurst")


def hurst_signal(returns: pd.Series, window: int = 252,
                 threshold: float = 0.55,
                 tqf_scale: float = 0.50) -> pd.Series:
    """Binary trend-quality multiplier based on rolling Hurst exponent.

    Returns 1.0 when H > threshold (persistent / trending),
    returns tqf_scale when H <= threshold (choppy / noisy).
    Shift(1) applied so computation does not look ahead.
    """
    h = rolling_hurst(returns, window=window)
    trending = (h > threshold)
    mult = trending.astype(float) + (~trending).astype(float) * tqf_scale
    mult = mult.fillna(1.0)
    return mult.shift(1).fillna(1.0).rename("TQF_Hurst")


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def trend_quality_summary(returns: pd.Series,
                          vr_q: int = 20,
                          vr_window: int = 126) -> dict:
    """Diagnostic summary of current trend quality metrics.

    Returns
    -------
    dict with:
        vr_current  : current VR(q) value
        vr_pct_trending : fraction of days in sample where VR > 1.0
        vr_regime   : 'trending' | 'choppy'
        pct_trending_1yr : fraction of last 252 days where VR > 1.0
    """
    vr = variance_ratio(returns, q=vr_q, window=vr_window).dropna()
    if len(vr) == 0:
        return {"error": "insufficient data"}

    vr_current = float(vr.iloc[-1])
    trending_mask = vr > 1.0
    pct_trending = float(trending_mask.mean())
    pct_trending_1yr = float(trending_mask.iloc[-TRADING_DAYS:].mean())

    return {
        "vr_q": vr_q,
        "vr_window": vr_window,
        "vr_current": round(vr_current, 4),
        "vr_regime": "trending" if vr_current > 1.0 else "choppy",
        "vr_pct_trending_full": round(pct_trending, 3),
        "vr_pct_trending_1yr": round(pct_trending_1yr, 3),
        "vr_mean": round(float(vr.mean()), 4),
        "vr_std": round(float(vr.std()), 4),
    }
