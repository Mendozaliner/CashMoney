"""Howard Marks Market Cycle Positioning Tool.

Implements Howard Marks' (Oaktree Capital) framework for measuring where we
stand in the market cycle, as described in "Mastering the Market Cycle" (2018)
and his famous memos. The cycle is observable through the behaviour of investors,
not from any single economic signal: expensive valuations + complacency +
strong momentum + improving fundamentals signal late cycle (time to be
defensive); the reverse signals early cycle (time to be aggressive).

Marks' seven cycle indicators (adapted to available data):
  1. Valuation (CAPE): high CAPE → rich → late cycle
  2. Credit / fear (VIX): low VIX → complacency → late cycle
  3. Price momentum (12m): strong positive → mid-to-late cycle
  4. Earnings quality (EPS growth): accelerating → mid cycle; decelerating → late
  5. Volatility of volatility (VIX 1m realised vol): low VoV → complacency
  6. Stock-bond correlation: positive corr (inflation regime) → late cycle risk
  7. Equity risk premium (1/CAPE - rf): low ERP → expensive → late cycle

Each indicator is converted to a 0-1 score where 1 means "maximum cycle risk"
(late cycle, be defensive) and 0 means "maximum opportunity" (early cycle,
be aggressive). The composite blends them with equal weights unless overridden.

References
----------
Marks, H. (2018). Mastering the Market Cycle. HarperBusiness.
Marks, H. (2000-2026). Oaktree Capital Memos (oaktreecapital.com).
Campbell & Shiller (1988). Stock Prices, Earnings, and Expected Dividends. J.Finance.
Ilmanen (2011). Expected Returns. Ch. 17 — Stock-Bond Correlation Regimes.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _rank_percentile(series: pd.Series, lookback: int | None = None) -> pd.Series:
    """Rolling historical percentile rank (0 = all-time low, 1 = all-time high).

    Args:
        series   : Input data series (daily).
        lookback : Rolling window in days; None = full history.
    """
    if lookback is None:
        return series.expanding().rank(pct=True)
    return series.rolling(lookback).rank(pct=True)


def valuation_score(shiller: pd.DataFrame,
                    daily_index: pd.DatetimeIndex,
                    lookback: int | None = None) -> pd.Series:
    """CAPE-based valuation cycle score (1 = richest/most dangerous).

    High CAPE → overvalued → late cycle risk. Uses the full available
    history for a stable percentile estimate.

    Args:
        shiller      : Shiller monthly DataFrame with a 'CAPE' column.
        daily_index  : Target daily DatetimeIndex to align the output to.
        lookback     : Rolling lookback for percentile (None = full history).
    """
    cape_col = next((c for c in shiller.columns if "cape" in c.lower() or
                     c.lower() in ("p/e10", "pe10", "cyclically adjusted")),
                    shiller.columns[-1])
    cape = shiller[cape_col].dropna()
    cape_rank = _rank_percentile(cape, lookback=lookback)
    return cape_rank.reindex(daily_index, method="ffill").ffill().fillna(0.5)


def fear_score(vix: pd.Series, lookback: int = 252 * 5) -> pd.Series:
    """VIX-level complacency score (1 = lowest VIX / most complacent = late cycle).

    Low VIX → investors are complacent → late cycle. Score is INVERTED
    from the raw VIX percentile so that 1 = dangerous (low fear).

    Args:
        vix      : Daily VIX close series.
        lookback : Rolling window for percentile (default 5 years).
    """
    vix_rank = _rank_percentile(vix, lookback=lookback)
    return 1.0 - vix_rank


def momentum_score(spy_close: pd.Series, lookback_months: int = 12) -> pd.Series:
    """12-month price momentum cycle score (1 = strong uptrend = mid/late cycle).

    Strong positive momentum signals mid-to-late cycle when prices have been
    rising for an extended period. Near-zero or negative momentum signals
    early cycle or bear market.

    Args:
        spy_close       : SPY daily close.
        lookback_months : Momentum lookback in calendar months (default 12).
    """
    days = int(lookback_months * 21)
    mom = spy_close.pct_change(periods=days)
    mom_rank = _rank_percentile(mom)
    return mom_rank.ffill().fillna(0.5)


def earnings_quality_score(shiller: pd.DataFrame,
                            daily_index: pd.DatetimeIndex) -> pd.Series:
    """EPS growth direction score (1 = strong growth = mid cycle; 0 = contracting).

    Marks notes that late-cycle environments feature decelerating earnings, not
    necessarily negative earnings. We use the 2nd derivative (change in growth
    rate) to capture deceleration. Simple implementation: 12m EPS growth as
    percentage of its 3-year rolling average — above average = cycle bullish.

    Args:
        shiller     : Shiller monthly DataFrame.
        daily_index : Target daily DatetimeIndex.
    """
    col = next((c for c in shiller.columns if "earn" in c.lower()), "Earnings")
    eps = shiller[col].dropna().ffill()
    growth_12m = eps.pct_change(12)
    avg_growth = growth_12m.rolling(36).mean()
    raw = (growth_12m - avg_growth).apply(lambda x: 1.0 if x >= 0 else 0.0)
    return raw.reindex(daily_index, method="ffill").ffill().fillna(0.5)


def equity_risk_premium_score(shiller: pd.DataFrame,
                               rf_daily: pd.Series,
                               daily_index: pd.DatetimeIndex) -> pd.Series:
    """Equity Risk Premium (ERP) cycle score (1 = lowest ERP = most expensive).

    ERP = earnings yield (1/CAPE) minus risk-free rate. Low ERP means equities
    offer little excess return over bonds — a hallmark of late-cycle richness.

    Args:
        shiller    : Shiller monthly DataFrame.
        rf_daily   : Daily risk-free rate (fraction per day).
        daily_index: Target daily DatetimeIndex.
    """
    cape_col = next((c for c in shiller.columns if "cape" in c.lower() or
                     c.lower() in ("p/e10", "pe10")), shiller.columns[-1])
    cape = shiller[cape_col].dropna().ffill()
    earnings_yield_monthly = 1.0 / cape.clip(1, None)

    rf_ann = rf_daily.reindex(earnings_yield_monthly.index, method="ffill").fillna(0.0) * 252
    erp = earnings_yield_monthly - rf_ann

    erp_rank = _rank_percentile(erp)
    inverted = 1.0 - erp_rank
    return inverted.reindex(daily_index, method="ffill").ffill().fillna(0.5)


def stock_bond_corr_score(spy_close: pd.Series,
                           ief_close: pd.Series,
                           corr_lb: int = 63) -> pd.Series:
    """Stock-bond correlation cycle score (1 = positive corr = inflation / late cycle).

    During late-cycle inflationary regimes, stocks and bonds both sell off
    (positive correlation). During deflationary recessions, they diverge
    (negative correlation = bonds rally as stocks fall = early-cycle).

    Args:
        spy_close : SPY daily close.
        ief_close : IEF daily close aligned to same index.
        corr_lb   : Rolling correlation lookback days (default 63 = 3 months).
    """
    spy_ret = spy_close.pct_change().fillna(0.0)
    ief_ret = ief_close.pct_change().fillna(0.0)
    rolling_corr = spy_ret.rolling(corr_lb).corr(ief_ret).fillna(0.0)
    corr_rank = _rank_percentile(rolling_corr)
    return corr_rank.ffill().fillna(0.5)


def composite_cycle_score(shiller: pd.DataFrame,
                           spy_close: pd.Series,
                           ief_close: pd.Series,
                           vix: pd.Series,
                           rf_daily: pd.Series,
                           weights: dict | None = None) -> pd.DataFrame:
    """Howard Marks composite market cycle score (0 = opportunity, 1 = risk).

    Blends five independent cycle indicators into a single daily score.
    Score near 1.0 means the market is signalling late-cycle danger (be defensive);
    score near 0.0 means early-cycle opportunity (be aggressive).

    This tool is INFORMATIONAL — it should NOT directly drive trading signals.
    Marks explicitly warns against market timing; the score is for context and
    risk-awareness, not for mechanical allocation.

    Args:
        shiller    : Shiller monthly DataFrame.
        spy_close  : SPY daily close.
        ief_close  : IEF daily close.
        vix        : VIX daily close.
        rf_daily   : Daily risk-free rate (fraction).
        weights    : Dict mapping component names to weights (must sum to 1.0).
                     Default: equal 20% to each of the five components.

    Returns:
        DataFrame with columns: valuation, fear, momentum, eps_quality,
        erp, cycle_score.
    """
    if weights is None:
        weights = {
            "valuation": 0.25,
            "fear":       0.20,
            "momentum":   0.20,
            "eps_quality": 0.20,
            "erp":        0.15,
        }

    idx = spy_close.index

    ief_aligned = ief_close.reindex(idx, method="ffill")
    vix_aligned = vix.reindex(idx, method="ffill")
    rf_aligned = rf_daily.reindex(idx, method="ffill").fillna(0.0)

    val = valuation_score(shiller, idx)
    fear = fear_score(vix_aligned)
    mom = momentum_score(spy_close)
    eps_q = earnings_quality_score(shiller, idx)
    erp = equity_risk_premium_score(shiller, rf_aligned, idx)

    cycle = (val * weights["valuation"]
             + fear * weights["fear"]
             + mom * weights["momentum"]
             + eps_q * weights["eps_quality"]
             + erp * weights["erp"])

    return pd.DataFrame({
        "valuation":  val,
        "fear":       fear,
        "momentum":   mom,
        "eps_quality": eps_q,
        "erp":        erp,
        "cycle_score": cycle,
    }, index=idx)


def cycle_summary(cycle_df: pd.DataFrame) -> dict:
    """Summarise current cycle position and long-run distribution.

    Args:
        cycle_df : Output of composite_cycle_score().

    Returns:
        Dict with current values, historical means, and a qualitative label.
    """
    current = cycle_df.iloc[-1]
    score = float(current["cycle_score"])

    if score >= 0.75:
        label = "late_cycle_risk"
    elif score >= 0.55:
        label = "mid_late_cycle"
    elif score >= 0.40:
        label = "mid_cycle_neutral"
    elif score >= 0.25:
        label = "early_mid_cycle"
    else:
        label = "early_cycle_opportunity"

    return {
        "current_score": round(score, 4),
        "cycle_label": label,
        "components": {
            col: round(float(current[col]), 4)
            for col in ["valuation", "fear", "momentum", "eps_quality", "erp"]
        },
        "history": {
            col: {
                "mean": round(float(cycle_df[col].mean()), 4),
                "std":  round(float(cycle_df[col].std()), 4),
            }
            for col in cycle_df.columns
        },
    }
