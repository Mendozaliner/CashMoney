"""Vectorized backtest engine for FRACTIONAL target exposures in [0, 1].

Complements backtest/engine.py (backtesting.py wrapper, binary long/flat only).
Needed for volatility-targeting overlays (session 2).

Timing contract (mirrors engine.py; cross-validated in
tests/test_vector_engine.py): a target exposure computed at bar t is filled at
bar t+1's close, so it first earns the t+1 -> t+2 close-to-close return:
effective position = signal.shift(2) against close-to-close returns.

Costs: `commission` fraction of traded notional |change in exposure| per fill
(0.1% default, same as engine.py). Optional `rf_daily` series credits the
un-invested fraction (1 - exposure) with the T-bill daily return; default
None = cash earns 0%, matching engine.py.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def strategy_returns(close: pd.Series, signal: pd.Series,
                     commission: float = 0.001,
                     rf_daily: pd.Series | None = None) -> pd.Series:
    r = close.pct_change().fillna(0.0)
    pos = signal.clip(0.0, 1.0).shift(2).fillna(0.0)
    turnover = pos.diff().abs().fillna(0.0)
    cost = commission * turnover
    cash = (1.0 - pos) * rf_daily.reindex(close.index).fillna(0.0) \
        if rf_daily is not None else 0.0
    return pos * r + cash - cost


def metrics(close, signal, commission=0.001, rf_daily=None, label="") -> dict:
    sr = strategy_returns(close, signal, commission, rf_daily)
    eq = (1.0 + sr).cumprod()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1
    r = sr[sr.index > sr.index[0]]
    sharpe = r.mean() / r.std() * np.sqrt(TRADING_DAYS) if r.std() > 0 else 0.0
    dn = r[r < 0].std()
    sortino = (r.mean() * TRADING_DAYS / (dn * np.sqrt(TRADING_DAYS))
               if dn and dn > 0 else np.nan)
    dd = (eq / eq.cummax() - 1.0).min()
    pos = signal.clip(0, 1).shift(2).fillna(0.0)
    to_yr = pos.diff().abs().sum() / years
    inv = r[pos.reindex(r.index) > 0]
    return {
        "label": label,
        "CAGR": round(cagr * 100, 2),
        "Sharpe": round(float(sharpe), 3),
        "Sortino": round(float(sortino), 3),
        "MaxDD": round(float(dd) * 100, 2),
        "DayWin%": round(float((inv > 0).mean() * 100), 1) if len(inv) else np.nan,
        "Turnover/yr": round(float(to_yr), 2),
        "AvgExposure": round(float(pos.mean()), 3),
        "End$per1k": round(1000 * float(eq.iloc[-1]), 2),
    }
