"""Volatility-targeting overlay on the champion trend filter (session 2).

Exposure_t = trend_t * min(1, target_vol / realized_vol_t), where trend is the
champion SMA200/3%-band long/flat gate and realized_vol is the annualized
std-dev of daily returns over `lookback` days. Capped at 1.0 (no leverage).

Research basis (see research/2026-07-13b-vol-targeting-cash-yield.md):
- Moreira & Muir (2017) J.Fin: scale by inverse variance -> higher Sharpe.
- Harvey et al. (2018) JPM: for risk assets, vol targeting raises Sharpe and
  cuts left tails; cap-at-1 keeps it long-only unlevered.
- Bongaerts, Kang & van Dijk (2020) FAJ: unconditional vol targeting churns;
  gating by the trend filter limits turnover to risk-on periods.
- Cederburg et al. (2020) JFE: skeptical OOS prior -- hence strict keep bar.

Tunable parameters (max 2): target_vol, lookback. Trend gate fixed at champion.
"""
import numpy as np
import pandas as pd

from strategies import sma_trend

DEFAULTS = {"target_vol": 0.15, "lookback": 20}
TRADING_DAYS = 252


def signals(close: pd.Series, target_vol: float = 0.15,
            lookback: int = 20) -> pd.Series:
    trend = sma_trend.signals(close, window=200, band=0.03)
    rv = close.pct_change().rolling(lookback).std() * np.sqrt(TRADING_DAYS)
    scale = (target_vol / rv).clip(upper=1.0)
    return (trend * scale).fillna(0.0).clip(0.0, 1.0)
