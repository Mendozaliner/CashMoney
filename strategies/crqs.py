"""Composite Regime-Quality Strategy (session 28, E42).

Combines two independently motivated signals:

    1. EQUITY QUALITY GATE (Lynch GARP / Graham EPS screen):
       Uses Shiller real earnings 12-month growth rate as a quality proxy.
       When the market's earnings trajectory is deteriorating (growth < threshold),
       scale down the equity position. This embeds Peter Lynch's GARP
       philosophy at the market level: only pay for equity beta when the
       earnings machine is running.

    2. REGIME-AWARE DEFENSIVE (Ilmanen/Dalio):
       Identical to E35 CRDS — cash sleeve switches between IEF (deflation
       regime, corr < threshold) and GLD (inflation regime, corr >= threshold)
       based on rolling stock-bond correlation. Most profitable discovery in
       defensive-sleeve research ($11,420 peak end$1k).

Signal pipeline per day:
    a. v2 base signal: vol_target(target_vol=0.18, lookback=20) with SMA200 gate.
    b. EPS quality multiplier: if EPS_growth < eps_threshold → equity_sig × scale_down
       else equity_sig unchanged. (The multiplier is shift-lagged 1 month + 1 day
       for publication lag.)
    c. Defensive allocation: remaining cash goes to IEF or GLD per corr regime.

Tunable parameters (max 12 configs):
    eps_threshold  ∈ {-0.05, 0.00, 0.05}   — EPS growth trigger (3 values)
    scale_down     ∈ {0.50, 0.75}            — equity scaling when quality fails (2)
    corr_threshold ∈ {-0.10, 0.00}           — stock-bond corr for inflation flag (2)
    Total: 3 × 2 × 2 = 12 configs (exactly at the cap).

References
----------
Lynch, P. (1989). "One Up on Wall Street". Simon & Schuster.
Shiller, R. (2000). "Irrational Exuberance". Princeton University Press.
Ilmanen, A. (2011). "Expected Returns". Wiley. Ch. 17.
Dalio, R. (2011). "How the Economic Machine Works". Bridgewater Associates.
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

DEFAULTS = {
    "eps_threshold": 0.00,   # EPS growth below which quality gate activates
    "scale_down": 0.50,      # equity multiplier when quality gate activates
    "corr_threshold": 0.00,  # stock-bond corr above which → inflation (GLD)
    "corr_lb": 63,           # rolling window for stock-bond correlation
    "eps_lookback_months": 12,
}

_EPS_LAG_MONTHS = 1          # Shiller data published with ~1-month lag
_IEF_SMA_WINDOW = 200
_GLD_SMA_WINDOW = 200


def _eps_quality_mask(shiller: pd.DataFrame,
                      daily_index: pd.DatetimeIndex,
                      eps_threshold: float,
                      eps_lookback_months: int = 12) -> pd.Series:
    """Return a boolean Series: True = EPS quality OK, False = quality gate fires.

    Uses Shiller real earnings 12-month growth, lagged 1 month for publication.
    """
    col = "Earnings" if "Earnings" in shiller.columns else shiller.columns[3]
    eps = shiller[col].ffill()
    eps_growth = eps.pct_change(periods=eps_lookback_months).shift(_EPS_LAG_MONTHS)
    eps_daily = (eps_growth
                 .reindex(daily_index, method="ffill")
                 .ffill()
                 .fillna(0.0))
    return eps_daily >= eps_threshold


def multi_signals(close: pd.Series,
                  shiller: pd.DataFrame,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  eps_threshold: float = DEFAULTS["eps_threshold"],
                  scale_down: float = DEFAULTS["scale_down"],
                  corr_threshold: float = DEFAULTS["corr_threshold"],
                  corr_lb: int = DEFAULTS["corr_lb"],
                  eps_lookback_months: int = DEFAULTS["eps_lookback_months"],
                  target_vol: float = 0.18,
                  lookback: int = 20) -> pd.DataFrame:
    """Weight schedule for the Composite Regime-Quality Strategy (E42).

    Returns a DataFrame with columns ['SPY', 'IEF', 'GLD'] where weights
    sum to at most 1.0 (remainder earns risk-free rate).

    Args:
        close               : SPY daily adjusted close.
        shiller             : Shiller monthly DataFrame from load_shiller().
        ief                 : IEF daily close (loaded if None).
        gld                 : GLD daily close (loaded if None).
        eps_threshold       : EPS 12m growth below which quality gate fires.
        scale_down          : Equity weight multiplier when gate fires (0-1).
        corr_threshold      : Rolling SPY-IEF corr above which → GLD hedge.
        corr_lb             : Days for rolling stock-bond correlation.
        eps_lookback_months : Months for EPS growth calculation.
        target_vol          : Vol-target annual volatility (champion 0.18).
        lookback            : Vol-target lookback in days (champion 20).
    """
    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]

    ief_a = ief.reindex(close.index, method="ffill")
    gld_a = gld.reindex(close.index, method="ffill")

    # ── 1. Base equity signal (v2) ────────────────────────────────────────
    spy_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    # ── 2. EPS quality gate ───────────────────────────────────────────────
    quality_ok = _eps_quality_mask(shiller, close.index, eps_threshold,
                                    eps_lookback_months)
    # When quality gate fires: scale down equity position
    quality_multiplier = quality_ok.astype(float)
    quality_multiplier[~quality_ok] = scale_down
    # shift(1): EPS quality known at end of month m, act at start of m+1
    quality_multiplier = quality_multiplier.shift(1).fillna(1.0)

    equity_sig = (spy_sig * quality_multiplier).clip(0.0, 1.0)

    # ── 3. Regime-aware defensive sleeve ──────────────────────────────────
    spy_ret = close.pct_change().fillna(0.0)
    ief_ret = ief_a.pct_change().fillna(0.0)

    rolling_corr = spy_ret.rolling(corr_lb).corr(ief_ret).fillna(0.0)
    inflation_flag = (rolling_corr >= corr_threshold).astype(float).shift(1).fillna(0.0)
    normal_flag = 1.0 - inflation_flag

    ief_gate = (ief_a > ief_a.rolling(_IEF_SMA_WINDOW).mean()).astype(float).shift(1).fillna(0.0)
    gld_gate = (gld_a > gld_a.rolling(_GLD_SMA_WINDOW).mean()).astype(float).shift(1).fillna(0.0)

    cash_avail = (1.0 - equity_sig).clip(0.0, 1.0)
    ief_weight = cash_avail * normal_flag * ief_gate
    gld_weight = cash_avail * inflation_flag * gld_gate

    return pd.DataFrame(
        {"SPY": equity_sig, "IEF": ief_weight, "GLD": gld_weight},
        index=close.index,
    )
