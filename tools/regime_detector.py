"""Economic regime detection tool (session 28, S28).

Implements Ray Dalio's 4-regime economic machine framework from Bridgewater's
"All Weather" research. Markets rotate through four regimes determined by two
axes:

    Growth axis    : real economic growth above or below expectations
    Inflation axis : inflation above or below expectations

Each regime favors different asset classes:
    BULL_GOLDILOCKS  : growth↑, inflation↓  → equities thrive
    BULL_INFLATION   : growth↑, inflation↑  → commodities + inflation bonds
    BEAR_DEFLATION   : growth↓, inflation↓  → nominal bonds, quality equities
    BEAR_STAGFLATION : growth↓, inflation↑  → gold, commodities, short bonds

Implementation uses observable signals as regime proxies:
    Growth proxy    : Shiller real EPS 12-month growth rate (pub. lag 1 month)
    Inflation proxy : Stock-bond correlation (negative = deflation,
                      positive = inflation) from Ilmanen (2011) Ch. 17

References
----------
Dalio, R. (2011). "How the Economic Machine Works". Bridgewater Associates.
Ilmanen, A. (2011). "Expected Returns". Wiley. Ch. 17.
Asness, C., Frazzini, A. & Pedersen, L.H. (2012). "Leverage Aversion and Risk
    Parity". Financial Analysts Journal 68(1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = ("bull_goldilocks", "bull_inflation", "bear_deflation", "bear_stagflation")

_DALIO_WEIGHTS = {
    "bull_goldilocks":  {"SPY": 0.80, "IEF": 0.10, "GLD": 0.10},
    "bull_inflation":   {"SPY": 0.50, "IEF": 0.20, "GLD": 0.30},
    "bear_deflation":   {"SPY": 0.20, "IEF": 0.70, "GLD": 0.10},
    "bear_stagflation": {"SPY": 0.10, "IEF": 0.20, "GLD": 0.70},
}


def _real_eps_growth(shiller: pd.DataFrame, lookback_months: int = 12,
                     lag_months: int = 1) -> pd.Series:
    """12-month growth rate of Shiller real earnings, lagged for publication."""
    col = "Earnings" if "Earnings" in shiller.columns else shiller.columns[3]
    eps = shiller[col].ffill()
    return eps.pct_change(periods=lookback_months).shift(lag_months)


def _stock_bond_corr(spy_close: pd.Series, ief_close: pd.Series,
                     lookback_days: int = 63) -> pd.Series:
    """Rolling daily return correlation between SPY and IEF."""
    spy_ret = spy_close.pct_change().fillna(0.0)
    ief_ret = ief_close.reindex(spy_close.index, method="ffill").pct_change().fillna(0.0)
    return spy_ret.rolling(lookback_days).corr(ief_ret).fillna(0.0)


def detect_regime(shiller: pd.DataFrame,
                  spy_close: pd.Series,
                  ief_close: pd.Series,
                  eps_growth_threshold: float = 0.0,
                  corr_threshold: float = 0.0,
                  corr_lookback: int = 63,
                  eps_lookback_months: int = 12) -> pd.DataFrame:
    """Classify each trading day into one of four Dalio economic regimes.

    Args:
        shiller               : Shiller monthly DataFrame from load_shiller().
        spy_close             : SPY daily close series.
        ief_close             : IEF daily close series.
        eps_growth_threshold  : EPS growth >= this -> 'growth' regime.
        corr_threshold        : Stock-bond corr >= this -> 'inflation' regime.
        corr_lookback         : Days for stock-bond correlation window.
        eps_lookback_months   : Months for EPS growth rate.

    Returns:
        DataFrame indexed on spy_close.index with columns:
            regime     : str from REGIMES
            growth_up  : bool
            inflation  : bool
            eps_growth : float
            sb_corr    : float
    """
    eps_gr_monthly = _real_eps_growth(shiller, eps_lookback_months)
    eps_gr_daily = (eps_gr_monthly
                    .reindex(spy_close.index, method="ffill")
                    .ffill()
                    .fillna(0.0))
    growth_up = (eps_gr_daily >= eps_growth_threshold)

    sb_corr = _stock_bond_corr(spy_close, ief_close, corr_lookback)
    inflation = (sb_corr >= corr_threshold)

    def _label(g: bool, i: bool) -> str:
        if g and not i:
            return "bull_goldilocks"
        if g and i:
            return "bull_inflation"
        if not g and not i:
            return "bear_deflation"
        return "bear_stagflation"

    regime = [_label(bool(g), bool(i)) for g, i in zip(growth_up, inflation)]

    return pd.DataFrame({
        "regime": regime,
        "growth_up": growth_up.values,
        "inflation": inflation.values,
        "eps_growth": eps_gr_daily.values,
        "sb_corr": sb_corr.values,
    }, index=spy_close.index)


def regime_weights(regime_series: pd.Series) -> pd.DataFrame:
    """Dalio-inspired target asset weights for each regime.

    Returns a DataFrame (date x asset) with suggested allocations.
    These are NOT the CashMoney champion weights; they are a research
    tool illustrating the All Weather philosophy.
    """
    rows = [_DALIO_WEIGHTS.get(r, _DALIO_WEIGHTS["bull_goldilocks"])
            for r in regime_series]
    return pd.DataFrame(rows, index=regime_series.index)


def regime_summary(regime_df: pd.DataFrame,
                   start: str | None = None,
                   end: str | None = None) -> dict:
    """Regime frequency and signal averages over a date range."""
    df = regime_df.loc[start:end] if (start or end) else regime_df
    counts = df["regime"].value_counts()
    total = len(df)
    return {
        "total_days": total,
        "regime_pct": {r: round(counts.get(r, 0) / total * 100, 1) for r in REGIMES},
        "avg_eps_growth": round(float(df["eps_growth"].mean()), 4),
        "avg_sb_corr": round(float(df["sb_corr"].mean()), 4),
    }
