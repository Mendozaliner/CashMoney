"""Multi-asset vectorized backtest engine for CashMoney (added session 5).

Extends vector_engine.py to handle portfolios spanning multiple tickers.

Interface:
    price_panel : pd.DataFrame  -- date x ticker, Close prices (adj).
    weights     : pd.DataFrame  -- date x ticker, fractional allocations.
                                   Row sums ≤ 1.0; residual earns rf or 0.

Timing contract matches vector_engine.py: weights computed at bar t fill at
t+1, first earning the t+1→t+2 close-to-close return, implemented as
weights.shift(2) vs daily returns.

Costs: commission fraction of total |Δweight| across all assets per bar.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def portfolio_returns(price_panel: pd.DataFrame, weights: pd.DataFrame,
                      commission: float = 0.0015,
                      rf_daily: pd.Series | None = None) -> pd.Series:
    """Daily portfolio return series from a multi-asset weight schedule.

    Args:
        price_panel : Wide close DataFrame (date x ticker).
        weights     : Wide weight DataFrame (date x ticker).
        commission  : Fraction of traded notional charged per rebalance.
        rf_daily    : Optional daily rf rate credited on uninvested fraction.
    """
    pan = price_panel.reindex(columns=weights.columns).copy()
    r = pan.pct_change().fillna(0.0)

    # shift(2): signal at t → executed at t+1 → earns return t+1→t+2
    w = weights.reindex(index=pan.index, columns=pan.columns).fillna(0.0)
    w_pos = w.shift(2).fillna(0.0)

    turnover = w_pos.diff().abs().sum(axis=1).fillna(0.0)
    cost = commission * turnover

    cash_frac = (1.0 - w_pos.sum(axis=1)).clip(lower=0.0)
    if rf_daily is not None:
        rf = rf_daily.reindex(pan.index).fillna(0.0)
        cash_ret = cash_frac * rf
    else:
        cash_ret = 0.0

    return ((w_pos * r).sum(axis=1) + cash_ret - cost).rename("portfolio")


def metrics(price_panel: pd.DataFrame, weights: pd.DataFrame,
            commission: float = 0.0015,
            rf_daily: pd.Series | None = None,
            label: str = "") -> dict:
    """Summary performance metrics for a multi-asset strategy."""
    sr = portfolio_returns(price_panel, weights, commission, rf_daily)
    eq = (1.0 + sr).cumprod()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1
    r = sr[sr.index > sr.index[0]]
    sharpe = r.mean() / r.std() * np.sqrt(TRADING_DAYS) if r.std() > 0 else 0.0
    dn = r[r < 0].std()
    sortino = (r.mean() * TRADING_DAYS / (dn * np.sqrt(TRADING_DAYS))
               if dn and dn > 0 else np.nan)
    dd = (eq / eq.cummax() - 1.0).min()
    w_pos = weights.reindex(price_panel.index).fillna(0.0).shift(2).fillna(0.0)
    to_yr = w_pos.diff().abs().sum(axis=1).sum() / years
    avg_invest = w_pos.sum(axis=1).mean()
    return {
        "label": label,
        "CAGR": round(cagr * 100, 2),
        "Sharpe": round(float(sharpe), 3),
        "Sortino": round(float(sortino), 3) if not np.isnan(sortino) else None,
        "MaxDD": round(float(dd) * 100, 2),
        "AvgInvested": round(float(avg_invest), 3),
        "Turnover/yr": round(float(to_yr), 2),
        "End$per1k": round(1000 * float(eq.iloc[-1]), 2),
    }
