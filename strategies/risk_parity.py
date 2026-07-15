"""Trend-gated naive risk parity (inverse-volatility) — session 8, 2026-07-15.

Philosophy: size positions by risk, not dollars, across genuinely different
asset classes (equity / duration / gold), and keep v2's trend gate so any
asset class in a downtrend hands its risk budget to T-bills instead of
averaging down. The gate is the desk's specific countermeasure to the 2022
risk-parity failure mode (bond overweight + stock/bond correlation flip).

Rules:
  1. Month-end: vol_i = trailing `lookback`-day std of daily returns.
     Raw weight w_i = (1/vol_i) / sum_ALL(1/vol_j) — budget set across the
     full panel, NOT renormalized when assets drop out.
  2. Asset included iff Close > SMA(200)*(1+band); excluded slots -> cash
     (T-bill sleeve handled by multi_engine).
  3. Weights held constant intra-month (ffilled daily), shift(2) execution.

Research basis (research/2026-07-15-s8-risk-parity.md):
- Asness, Frazzini & Pedersen (2012) "Leverage Aversion and Risk Parity".
- Maillard, Roncalli & Teiletche (2010) ERC portfolios (1/vol = naive case).
- "Risk Without Return" (arXiv 1307.0114) — bond-carry critique.
- Allocate Smartly / CXO on trend + RP combinations; MPI/CAIA on 2022 failure.

Parameters (max 2): lookback (vol window, days), band (SMA buffer).
"""
import numpy as np
import pandas as pd

DEFAULT_ASSETS = ["SPY", "IEF", "GLD"]
SMA_WINDOW = 200
DEFAULTS = {"lookback": 60, "band": 0.0}


def multi_signals(price_panel: pd.DataFrame, lookback: int = 60,
                  band: float = 0.0, assets=None) -> pd.DataFrame:
    """Weight DataFrame (date x ticker): inverse-vol slots gated on SMA200."""
    assets = [a for a in (assets or DEFAULT_ASSETS) if a in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if not assets:
        return weights

    px = price_panel[assets]
    ret = px.pct_change()
    vol = ret.rolling(lookback).std()
    inv = 1.0 / vol
    # Budget across the FULL panel: NaN vol (insufficient history) = no slot,
    # and its share of the budget sits in cash rather than inflating others.
    raw = inv.div(inv.sum(axis=1, skipna=True), axis=0)

    sma = px.rolling(SMA_WINDOW).mean()
    on = px.gt(sma * (1.0 + band)) & sma.notna() & vol.notna()

    gated = raw.where(on, 0.0).fillna(0.0)

    # Month-end decisions held through the following month.
    month_end = pd.Series(True, index=px.index).groupby(
        [px.index.year, px.index.month]).tail(1).index
    gated_me = gated.loc[gated.index.isin(month_end)]
    daily = gated_me.reindex(px.index).ffill().fillna(0.0)

    weights[assets] = daily[assets]
    # Safety: row sums must never exceed 1 (cash sleeve non-negative).
    s = weights.sum(axis=1)
    over = s > 1.0
    if over.any():
        weights.loc[over] = weights.loc[over].div(s[over], axis=0)
    return weights
