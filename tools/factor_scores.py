"""Factor scoring tools (session 28, S28).

Market-level factor scores derived from publicly available macro data:

    Graham safety score  : CAPE-based margin of safety (Graham 1949)
    Buffett ERP          : Earnings yield vs T-bill (Buffett/Bogle ERP)
    Lynch GARP score     : PEG proxy — EPS growth / CAPE (Lynch 1989)
    Momentum score       : 12−1 price momentum (Jegadeesh & Titman 1993;
                           Carhart 1997)
    Composite quality    : Equal-weight average of the above four

All scores are designed for market-level (SPY) timing rather than
individual stock selection. They serve as signal inputs to regime-
aware strategies.

References
----------
Graham, B. & Dodd, D. (1949). "Security Analysis". McGraw-Hill.
Lynch, P. (1989). "One Up on Wall Street". Simon & Schuster.
Buffett, W. (2001). "Warren Buffett on the Stock Market". Fortune.
Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners...".
    Journal of Finance 48(1).
Carhart, M.M. (1997). "On Persistence in Mutual Fund Performance".
    Journal of Finance 52(1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── Graham safety score ───────────────────────────────────────────────────

def graham_safety_score(shiller: pd.DataFrame,
                        cape_safe: float = 15.0,
                        cape_danger: float = 35.0) -> pd.Series:
    """CAPE-based margin of safety score, reindexed to daily frequency.

    Score = 1.0 when CAPE ≤ cape_safe (maximum safety / cheapness).
    Score = 0.0 when CAPE ≥ cape_danger (expensive / no margin of safety).
    Linearly interpolated between.

    Args:
        shiller      : Shiller monthly DataFrame from load_shiller().
        cape_safe    : CAPE below which the market is considered safe.
        cape_danger  : CAPE above which safety is zero.

    Returns:
        Monthly Series of safety scores ∈ [0, 1].
    """
    col = "CAPE" if "CAPE" in shiller.columns else shiller.columns[1]
    cape = shiller[col].ffill()
    score = 1.0 - (cape - cape_safe) / (cape_danger - cape_safe)
    return score.clip(0.0, 1.0).rename("graham_safety")


def graham_safety_daily(shiller: pd.DataFrame,
                        daily_index: pd.DatetimeIndex,
                        cape_safe: float = 15.0,
                        cape_danger: float = 35.0) -> pd.Series:
    """graham_safety_score() forward-filled to a daily trading index."""
    monthly = graham_safety_score(shiller, cape_safe, cape_danger)
    return (monthly
            .reindex(daily_index, method="ffill")
            .ffill()
            .fillna(0.5)
            .rename("graham_safety"))


# ── Buffett ERP ───────────────────────────────────────────────────────────

def earnings_yield_vs_bonds(shiller: pd.DataFrame,
                             rf_daily: pd.Series | None = None) -> pd.Series:
    """Equity Risk Premium proxy: 1/CAPE − risk-free rate.

    Buffett's rule of thumb: buy equities when earnings yield materially
    exceeds bond yield. Positive ERP → equities attractive vs cash/bonds.

    Args:
        shiller    : Shiller monthly DataFrame.
        rf_daily   : Daily risk-free rate series (annualised fraction).
                     If None, uses zero (ignores the bond side).

    Returns:
        Monthly Series of ERP (float). Not clipped — can be negative.
    """
    col = "CAPE" if "CAPE" in shiller.columns else shiller.columns[1]
    cape = shiller[col].ffill()
    earnings_yield = 1.0 / cape  # annualised

    if rf_daily is not None:
        # Convert daily rf to monthly; align to Shiller index
        rf_monthly = rf_daily.resample("ME").mean().reindex(
            cape.index, method="ffill").fillna(0.0)
        erp = earnings_yield - rf_monthly * 252
    else:
        erp = earnings_yield

    return erp.rename("erp")


def erp_daily(shiller: pd.DataFrame,
              daily_index: pd.DatetimeIndex,
              rf_daily: pd.Series | None = None) -> pd.Series:
    """earnings_yield_vs_bonds() forward-filled to a daily trading index."""
    monthly = earnings_yield_vs_bonds(shiller, rf_daily)
    return (monthly
            .reindex(daily_index, method="ffill")
            .ffill()
            .fillna(0.0)
            .rename("erp"))


# ── Lynch GARP score ──────────────────────────────────────────────────────

def garp_score(shiller: pd.DataFrame,
               growth_lookback_months: int = 12,
               normalize: bool = True) -> pd.Series:
    """Lynch PEG proxy: EPS growth rate divided by CAPE-based P/E.

    Peter Lynch's PEG ratio — Growth / P/E — but applied at market level:
        growth    = Shiller real EPS 12-month change (%)
        valuation = CAPE (acts as cyclically adjusted P/E)
        GARP_raw  = growth / CAPE

    A high GARP score means earnings are growing fast relative to
    the price you pay. Lynch considered PEG < 1.0 attractive.

    When normalize=True the score is winsorised (1st/99th percentile) and
    then scaled to [0, 1] over the full sample for comparability with
    other factor scores.

    Args:
        shiller               : Shiller monthly DataFrame.
        growth_lookback_months: Window for EPS growth calculation.
        normalize             : If True, return a [0,1]-normalised series.

    Returns:
        Monthly Series.
    """
    eps_col = "Earnings" if "Earnings" in shiller.columns else shiller.columns[3]
    cape_col = "CAPE" if "CAPE" in shiller.columns else shiller.columns[1]

    eps = shiller[eps_col].ffill()
    cape = shiller[cape_col].ffill()

    eps_growth = eps.pct_change(periods=growth_lookback_months) * 100
    raw = eps_growth / cape.replace(0, np.nan)

    if normalize:
        lo = raw.quantile(0.01)
        hi = raw.quantile(0.99)
        raw = raw.clip(lo, hi)
        raw = (raw - lo) / (hi - lo + 1e-12)

    return raw.rename("garp")


def garp_daily(shiller: pd.DataFrame,
               daily_index: pd.DatetimeIndex,
               growth_lookback_months: int = 12,
               normalize: bool = True) -> pd.Series:
    """garp_score() forward-filled to a daily trading index."""
    monthly = garp_score(shiller, growth_lookback_months, normalize)
    return (monthly
            .reindex(daily_index, method="ffill")
            .ffill()
            .fillna(0.5)
            .rename("garp"))


# ── Momentum score ────────────────────────────────────────────────────────

def price_momentum_score(close: pd.Series,
                         short_lb: int = 21,
                         long_lb: int = 252,
                         normalize: bool = True) -> pd.Series:
    """12−1 month price momentum (Jegadeesh & Titman / Carhart).

    Classic "12-1" momentum: 12-month return skipping the most recent
    month to avoid short-term reversal. Positive → price trending up.

    When normalize=True the score is winsorised and scaled to [0, 1].

    Args:
        close      : Daily closing price series.
        short_lb   : Days to skip at the end (1 month ≈ 21 days).
        long_lb    : Total lookback (12 months ≈ 252 days).
        normalize  : If True, return a [0,1]-normalised series.

    Returns:
        Daily Series.
    """
    mom = close.shift(short_lb) / close.shift(long_lb) - 1

    if normalize:
        lo = mom.quantile(0.01)
        hi = mom.quantile(0.99)
        mom = mom.clip(lo, hi)
        mom = (mom - lo) / (hi - lo + 1e-12)

    return mom.fillna(0.5).rename("momentum")


# ── Composite quality score ───────────────────────────────────────────────

def composite_quality_score(shiller: pd.DataFrame,
                             spy_close: pd.Series,
                             rf_daily: pd.Series | None = None,
                             cape_safe: float = 15.0,
                             cape_danger: float = 35.0,
                             garp_lookback_months: int = 12,
                             mom_short_lb: int = 21,
                             mom_long_lb: int = 252,
                             weights: tuple[float, ...] = (0.25, 0.25, 0.25, 0.25)
                             ) -> pd.DataFrame:
    """Equal- (or custom) weighted composite of four factor scores.

    Combines Graham safety, Buffett ERP, Lynch GARP, and price momentum
    into a single [0, 1] composite on the daily trading calendar.

    Args:
        shiller             : Shiller monthly DataFrame.
        spy_close           : SPY daily close (sets the output index).
        rf_daily            : Daily risk-free rate for ERP calculation.
        cape_safe           : Graham safety CAPE floor.
        cape_danger         : Graham safety CAPE ceiling.
        garp_lookback_months: Months for EPS growth in GARP.
        mom_short_lb        : Days skipped in momentum (reversal buffer).
        mom_long_lb         : Total momentum lookback days.
        weights             : (w_graham, w_erp, w_garp, w_momentum).
                              Must sum to 1.0.

    Returns:
        DataFrame indexed on spy_close.index with columns:
            graham_safety, erp_norm, garp, momentum, composite
    """
    idx = spy_close.index

    g = graham_safety_daily(shiller, idx, cape_safe, cape_danger)

    # ERP normalised to [0,1]
    erp_raw = erp_daily(shiller, idx, rf_daily)
    erp_lo, erp_hi = erp_raw.quantile(0.01), erp_raw.quantile(0.99)
    e = ((erp_raw - erp_lo) / (erp_hi - erp_lo + 1e-12)).clip(0.0, 1.0).rename("erp_norm")

    garp = garp_daily(shiller, idx, garp_lookback_months)
    mom = price_momentum_score(spy_close, mom_short_lb, mom_long_lb)

    w = weights
    composite = w[0] * g + w[1] * e + w[2] * garp + w[3] * mom

    return pd.DataFrame({
        "graham_safety": g.values,
        "erp_norm": e.values,
        "garp": garp.values,
        "momentum": mom.values,
        "composite": composite.values,
    }, index=idx)


def factor_summary(factor_df: pd.DataFrame,
                   start: str | None = None,
                   end: str | None = None) -> dict:
    """Summary statistics for factor scores over a date range."""
    df = factor_df.loc[start:end] if (start or end) else factor_df
    return {
        col: {
            "mean": round(float(df[col].mean()), 4),
            "std":  round(float(df[col].std()), 4),
            "min":  round(float(df[col].min()), 4),
            "max":  round(float(df[col].max()), 4),
            "current": round(float(df[col].iloc[-1]), 4),
        }
        for col in df.columns
    }
