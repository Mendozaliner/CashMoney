"""CRQS-CycleOverlay (session 30, E45).

Extends the CRQS champion with a Howard Marks market-cycle tilt.

Philosophy
----------
Howard Marks (Oaktree Capital, "Mastering the Market Cycle" 2018) argues that
the best risk management is knowing WHERE you are in the market cycle.  Late-
cycle environments share common signatures: rich valuations (high CAPE), investor
complacency (low VIX), elevated prices relative to history (high momentum).  When
these conditions align — and earnings are still growing (the EPS quality gate is
NOT already firing) — there is a quiet, insidious risk: everything looks fine,
so capital allocators take maximum risk exactly when they should be cautious.

The CRQS champion already handles the "bad" scenario (earnings falling, inflation
regime) via its EPS quality gate and regime-aware defensive sleeve.  What it
misses is the "dangerous good times" scenario — a late-cycle bull market with
rising earnings and low volatility, where the cycle overlay adds a modest,
pre-emptive defensive tilt.

Signal pipeline
---------------
1. Compute CRQS base weights (v2 trend × vol_target × EPS quality gate × regime sleeve).
2. Compute Howard Marks composite cycle score from:
       0.25 × CAPE valuation percentile
     + 0.20 × (1 - VIX percentile) [low VIX = complacency = late cycle]
     + 0.20 × 12-month momentum percentile
     + 0.15 × (1 - ERP percentile) [low ERP = expensive equity = late cycle]
   (The EPS quality component is deliberately EXCLUDED — CRQS already handles it.)
3. Normalise the 4-component score to [0, 1] by dividing by the total weight (0.80).
4. Cycle tilt fires when:
       normalised_cycle_score > cycle_threshold
       AND
       EPS quality gate is INACTIVE (eps_growth >= 0, i.e. earnings not falling)
   → multiply the CRQS SPY weight by cycle_scale (e.g., 0.85).
   Rationale: when earnings ARE falling, CRQS already reduced equity to 75%; the
   cycle overlay does not pile on.  The overlay fires only in the "complacent late
   bull" scenario that CRQS would otherwise ride fully invested.

Parameters (max 12 configs, exactly 6 used)
-------------------------------------------
  cycle_threshold : float ∈ {0.70, 0.75, 0.80}  — score above which tilt fires
  cycle_scale     : float ∈ {0.80, 0.90}          — SPY-weight multiplier when tilt on
  Total: 3 × 2 = 6 configs.

References
----------
Marks, H. (2018). Mastering the Market Cycle. HarperBusiness.
Shiller, R.J. & Campbell, J.Y. (1988). Stock Prices, Earnings, and Expected Dividends.
Ilmanen, A. (2011). Expected Returns. Wiley. Ch. 17.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from strategies import vol_target
from strategies.crqs import _eps_quality_mask
from data.loader import load_ohlcv, load_shiller

DEFAULTS = {
    "eps_threshold": 0.00,    # EPS quality gate threshold (same as CRQS champion)
    "scale_down": 0.75,       # EPS quality scale-down factor (same as champion)
    "corr_threshold": 0.00,   # regime switch threshold (same as champion)
    "corr_lb": 63,            # rolling corr lookback (same as champion)
    "cycle_threshold": 0.70,  # Marks score above which tilt activates
    "cycle_scale": 0.90,      # SPY-weight multiplier when tilt is on
    "vix_lb": 252 * 5,        # VIX percentile lookback (5 years, same as market_cycle.py)
}

_IEF_SMA = 200
_GLD_SMA = 200


def _marks_4component_score(shiller: pd.DataFrame,
                             spy_close: pd.Series,
                             ief_close: pd.Series,
                             vix: pd.Series,
                             rf_daily: pd.Series,
                             vix_lb: int = 252 * 5) -> pd.Series:
    """Howard Marks 4-component cycle score (EPS quality excluded — CRQS handles it).

    Returns a daily Series in [0, 1]:  0 = opportunity, 1 = late-cycle danger.
    Each component uses rolling historical percentile to avoid any look-ahead.

    Components and weights (sum to 0.80; renormalised to [0,1]):
        0.25  valuation (CAPE percentile)
        0.20  fear      (1 - VIX percentile, low VIX = complacent)
        0.20  momentum  (12-month price momentum percentile)
        0.15  erp       (1 - ERP percentile, low ERP = expensive equity)
    """
    idx = spy_close.index

    # 1. Valuation: CAPE expanding percentile
    cape_col = next(
        (c for c in shiller.columns
         if "cape" in c.lower() or c.lower() in ("p/e10", "pe10")),
        shiller.columns[-1]
    )
    cape = shiller[cape_col].dropna()
    cape_rank = cape.expanding().rank(pct=True)
    val_score = cape_rank.reindex(idx, method="ffill").ffill().fillna(0.5)

    # 2. Fear: low VIX = complacency = late cycle (inverted)
    vix_a = vix.reindex(idx, method="ffill")
    vix_rank = vix_a.rolling(vix_lb).rank(pct=True)
    fear_score = (1.0 - vix_rank).fillna(0.5)

    # 3. Momentum: 12-month price momentum expanding percentile
    mom_12 = spy_close.pct_change(252)
    mom_rank = mom_12.expanding().rank(pct=True)
    mom_score = mom_rank.ffill().fillna(0.5)

    # 4. ERP: 1/CAPE − rf; low ERP = expensive equity (inverted)
    rf_ann = rf_daily.reindex(shiller.index, method="ffill").fillna(0.0) * 252
    ey = (1.0 / cape.clip(1, None))
    erp = (ey - rf_ann).reindex(idx, method="ffill").ffill()
    erp_rank = erp.expanding().rank(pct=True)
    erp_score = (1.0 - erp_rank).fillna(0.5)

    # Blend (raw sum = 0.25+0.20+0.20+0.15 = 0.80; renormalise to [0,1])
    raw = 0.25 * val_score + 0.20 * fear_score + 0.20 * mom_score + 0.15 * erp_score
    return (raw / 0.80).clip(0.0, 1.0)


def multi_signals(close: pd.Series,
                  shiller: pd.DataFrame,
                  vix: pd.Series,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  rf_daily: pd.Series | None = None,
                  eps_threshold: float = DEFAULTS["eps_threshold"],
                  scale_down: float = DEFAULTS["scale_down"],
                  corr_threshold: float = DEFAULTS["corr_threshold"],
                  corr_lb: int = DEFAULTS["corr_lb"],
                  cycle_threshold: float = DEFAULTS["cycle_threshold"],
                  cycle_scale: float = DEFAULTS["cycle_scale"],
                  vix_lb: int = DEFAULTS["vix_lb"],
                  target_vol: float = 0.18,
                  lookback: int = 20) -> pd.DataFrame:
    """Weight schedule for the CRQS-CycleOverlay (E45).

    Returns a DataFrame with columns ['SPY', 'IEF', 'GLD'] where weights
    sum to at most 1.0 (remainder earns risk-free rate or T-bill yield).
    """
    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]
    if rf_daily is None:
        rf_daily = load_ohlcv("^IRX")["Close"] / 100 / 252

    ief_a = ief.reindex(close.index, method="ffill")
    gld_a = gld.reindex(close.index, method="ffill")

    # ── 1. Base equity signal (v2) ────────────────────────────────────────────
    spy_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    # ── 2. EPS quality gate (same as CRQS) ───────────────────────────────────
    quality_ok = _eps_quality_mask(shiller, close.index, eps_threshold, 12)
    quality_mult = quality_ok.astype(float)
    quality_mult[~quality_ok] = scale_down
    quality_mult = quality_mult.shift(1).fillna(1.0)

    equity_sig = (spy_sig * quality_mult).clip(0.0, 1.0)

    # ── 3. Howard Marks cycle tilt ────────────────────────────────────────────
    #  Fires only when quality gate is INACTIVE (earnings growing).
    #  shift(1): cycle score known at close t, tilt applies from t+1 onwards.
    vix_a = vix.reindex(close.index, method="ffill")
    rf_a = rf_daily.reindex(close.index, method="ffill").fillna(0.0)
    cycle_raw = _marks_4component_score(
        shiller, close, ief_a, vix_a, rf_a, vix_lb=vix_lb
    )
    late_cycle = (cycle_raw > cycle_threshold).astype(float).shift(1).fillna(0.0)

    # quality_ok shifted by 1 (already shifted above, re-derive the pre-shift version)
    quality_ok_d1 = quality_ok.astype(float).shift(1).fillna(1.0)  # 1=ok, 0=gate fired
    gate_inactive = quality_ok_d1  # tilt fires only when eps_quality is fine

    # Cycle tilt: reduce equity when late cycle AND gate inactive
    cycle_active = late_cycle * gate_inactive
    cycle_mult = 1.0 - cycle_active * (1.0 - cycle_scale)   # [0.80, 1.00]

    equity_sig = (equity_sig * cycle_mult).clip(0.0, 1.0)

    # ── 4. Regime-aware defensive sleeve (same as CRQS) ──────────────────────
    spy_ret = close.pct_change().fillna(0.0)
    ief_ret = ief_a.pct_change().fillna(0.0)
    rolling_corr = spy_ret.rolling(corr_lb).corr(ief_ret).fillna(0.0)
    inflation_flag = (rolling_corr >= corr_threshold).astype(float).shift(1).fillna(0.0)
    normal_flag = 1.0 - inflation_flag

    ief_gate = (ief_a > ief_a.rolling(_IEF_SMA).mean()).astype(float).shift(1).fillna(0.0)
    gld_gate = (gld_a > gld_a.rolling(_GLD_SMA).mean()).astype(float).shift(1).fillna(0.0)

    cash_avail = (1.0 - equity_sig).clip(0.0, 1.0)
    ief_weight = cash_avail * normal_flag * ief_gate
    gld_weight = cash_avail * inflation_flag * gld_gate

    return pd.DataFrame(
        {"SPY": equity_sig, "IEF": ief_weight, "GLD": gld_weight},
        index=close.index,
    )
