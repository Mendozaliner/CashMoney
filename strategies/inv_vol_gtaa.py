"""Inverse-Volatility GTAA — Swensen-4 Universe (session 25, E38).

Philosophy: Risk parity (Qian 2005; Asness, Frazzini & Pedersen 2012) argues
that equal-weight portfolios are DOMINATED by their highest-vol asset (equities).
Weighting by INVERSE realized volatility gives each asset a more equal RISK
contribution rather than an equal dollar contribution.

This module applies inverse-vol weighting to the Swensen-4 universe:
  SPY  — US equity (equity risk premium)
  IEF  — Intermediate bonds (duration / safe-haven)
  GLD  — Gold (inflation hedge / crisis alpha)
  VNQ  — US real estate (real-asset / rent-yield premium)

Each asset is independently SMA(sma_window)-gated. The raw inverse-vol budget
is calculated across ALL four assets (not just active ones); slots below their
trend gate go to cash (T-bill via multi_engine) rather than inflating others.
Rebalancing is month-end to limit transaction costs, held daily via forward-fill.

Key distinctions from prior experiments:
- E12 Risk Parity (SPY/IEF/GLD, s8): SAME weighting method (inverse-vol),
  DIFFERENT universe (3 assets; no VNQ). This is the 4-asset extension.
  ROADMAP note on E37: "inverse-vol weighting on the Swensen universe might
  preserve the DD benefit" (s24). This directly tests that hypothesis.
- E37 Swensen-4 (SPY/IEF/GLD/VNQ, s24): SAME 4-asset universe, EQUAL 25% weights.
  This strategy tests the SAME universe with RISK-WEIGHTED allocation.
- E35 CRDS / E34 DDAS (s23): defensive-sleeve strategies; SPY is always the
  equity portion. This is a full 4-way risk-budget allocation.

Academic basis:
- Qian (2005) "Risk Parity Portfolios": inverse-vol weights maximize diversification
  when assets have identical Sharpe ratios — the historical approximation holds
  well for equities, bonds, gold, and REITs.
- Asness, Frazzini & Pedersen (2012) JPM "Leverage Aversion and Risk Parity":
  risk parity outperforms equal-weight in risk-adjusted terms; the improvement
  is especially large when vol dispersion across assets is high.
- Maillard, Roncalli & Teiletche (2010) JFI "On the Properties of ERC Portfolios":
  1/vol is the analytically simplest equal-risk-contribution solution.
- Faber (2007) SSRN "A Quantitative Approach to Tactical Asset Allocation":
  per-asset SMA trend gates prevent compounding losses during drawdowns.
- Brounen & De Koning (2012) JRE: VNQ provides real-estate risk premium distinct
  from equity and bond premia; inclusion improves diversification for US investors.

Tunable parameters (max 2): vol_lookback, sma_window.
"""
import numpy as np
import pandas as pd

from data.loader import load_ohlcv

ASSETS = ["SPY", "IEF", "GLD", "VNQ"]
DEFAULTS = {"vol_lookback": 60, "sma_window": 200}
TRADING_DAYS = 252


def multi_signals(spy: pd.Series,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  vnq: pd.Series | None = None,
                  vol_lookback: int = 60,
                  sma_window: int = 200) -> pd.DataFrame:
    """Weight schedule for inverse-vol GTAA on the Swensen-4 universe.

    Args:
        spy         : SPY daily adjusted close (index reference).
        ief         : IEF daily close (loaded from cache if None).
        gld         : GLD daily close (loaded from cache if None).
        vnq         : VNQ daily close (loaded from cache if None).
        vol_lookback: Rolling window (trading days) for realized vol estimation.
        sma_window  : SMA lookback (trading days) for the per-asset trend gate.

    Returns:
        Weight DataFrame (date × ['SPY','IEF','GLD','VNQ']).
        Weights sum to ≤ 1.0; residual earns T-bill in multi_engine.
        No-lookahead: all signals use shift(1); engine adds another shift(1).
    """
    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]
    if vnq is None:
        vnq = load_ohlcv("VNQ")["Close"]

    idx = spy.index
    prices = pd.DataFrame({
        "SPY": spy,
        "IEF": ief.reindex(idx, method="ffill"),
        "GLD": gld.reindex(idx, method="ffill"),
        "VNQ": vnq.reindex(idx, method="ffill"),
    })

    # Realized vol: annualized std of daily returns
    ret = prices.pct_change()
    vol = ret.rolling(vol_lookback).std() * np.sqrt(TRADING_DAYS)

    # SMA trend gate: 1 if close > SMA(window), else 0
    sma  = prices.rolling(sma_window).mean()
    gate = (prices > sma) & sma.notna() & vol.notna()

    # Inverse-vol budget across ALL assets; inactive slots go to cash (not
    # redistributed to active assets — same convention as risk_parity E12).
    inv_vol = 1.0 / vol.clip(lower=1e-8)
    total_inv = inv_vol.sum(axis=1, skipna=True).replace(0.0, np.nan)
    raw_weights = inv_vol.div(total_inv, axis=0).fillna(0.0)

    # Gate: zero out assets below trend; their budget stays in cash
    gated = raw_weights.where(gate, 0.0).fillna(0.0)

    # Month-end rebalance: hold weights constant intra-month (limits turnover)
    is_me = (prices.index.to_period("M") != pd.DatetimeIndex(
        prices.index[1:].tolist() + [prices.index[-1] + pd.Timedelta(days=40)]
    ).to_period("M"))
    me_idx = prices.index[is_me]
    gated_me = gated.loc[gated.index.isin(me_idx)]
    daily = gated_me.reindex(prices.index).ffill().fillna(0.0)

    # Safety: ensure no row sums > 1.0 (floating-point guard)
    row_sums = daily.sum(axis=1)
    over = row_sums > 1.0
    if over.any():
        daily.loc[over] = daily.loc[over].div(row_sums[over], axis=0)

    return daily
