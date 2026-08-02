"""Minimum Variance Portfolio (Markowitz 1952) — session 27, E41.

Allocates across SPY, IEF, and GLD by minimizing portfolio variance using a
rolling empirical covariance matrix. Implements Harry Markowitz's foundational
mean-variance insight: the minimum-variance portfolio achieves the lowest
possible volatility for a given set of assets by exploiting negative or low
cross-correlations.

This is the theoretically sound lower-bound on portfolio volatility and differs
from all prior experiments:
  - vs risk_parity (E12):  RP uses 1/σ diagonal weights; MinVar uses the full
    covariance matrix Σ, allowing it to allocate MORE to an asset when its
    covariances with other assets are low or negative.
  - vs IVG (E38): IVG uses SMA gate per asset + inverse-vol weights; MinVar
    derives weights analytically from Σ, not per-asset volatilities.
  - vs Permanent Portfolio (E14): PP uses fixed 25/25/25/25 mix; MinVar adapts
    weights dynamically to the realized correlation structure.

Long-only constraint is imposed via clip-then-renormalize on the analytical
unconstrained solution (DeMiguel et al. 2009 RFS show this approximation
performs on par with full QP solvers for monthly-rebalanced portfolios).

Rebalance: month-end only, to limit turnover.

Research basis:
- Markowitz, H. (1952) J.Finance: Portfolio Selection.
- Clarke, De Silva & Thorley (2006, 2013) JPM: MinVar earns near-market
  returns with ~25-30% lower volatility in US equities.
- DeMiguel, Garlappi & Uppal (2009) RFS: long-only MinVar approximation
  competitive with exact QP solver out-of-sample.
- Ilmanen (2011): bond-equity correlation is negative in deflationary
  environments (the classic environment where MinVar favours bonds heavily)
  and flips positive in inflation — precisely the regime IEF/GLD rotation
  exploits in the sma_gate=True variant.

Parameters (max 2): cov_lookback (int), sma_gate (bool).
"""
import numpy as np
import pandas as pd

DEFAULT_ASSETS = ["SPY", "IEF", "GLD"]
SMA_WINDOW = 200
DEFAULTS = {"cov_lookback": 60, "sma_gate": True}


def _min_var_weights(cov: np.ndarray) -> np.ndarray:
    """Analytical long-only minimum variance weights.

    1. Unconstrained MV solution: w* = Σ⁻¹ 1 / (1'Σ⁻¹ 1)
    2. Clip negatives (long-only constraint).
    3. Renormalize to sum to 1.

    Falls back to equal weights if the matrix is singular or all-negative.
    """
    n = cov.shape[0]
    if n == 1:
        return np.array([1.0])
    try:
        ones = np.ones(n)
        inv_cov = np.linalg.inv(cov + np.eye(n) * 1e-10)  # mild ridge for stability
        raw = inv_cov @ ones
        raw = raw / (ones @ inv_cov @ ones)
        w = np.clip(raw, 0.0, None)
        total = w.sum()
        if total > 1e-12:
            return w / total
    except np.linalg.LinAlgError:
        pass
    return np.ones(n) / n


def multi_signals(price_panel: pd.DataFrame, cov_lookback: int = 60,
                  sma_gate: bool = True, assets=None) -> pd.DataFrame:
    """Weight DataFrame (date × ticker): MinVar weights, month-end rebalance.

    Args:
        price_panel  : Wide close-price DataFrame (date × ticker).
        cov_lookback : Rolling window (days) for covariance estimation.
        sma_gate     : If True, SPY is excluded from the optimiser when
                       SPY close < SMA(200); the budget is reallocated
                       between IEF and GLD.
        assets       : Subset of columns to use; defaults to DEFAULT_ASSETS.
    """
    assets = [a for a in (assets or DEFAULT_ASSETS) if a in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if not assets:
        return weights

    px = price_panel[assets].copy()
    ret = px.pct_change()
    sma_spy = px["SPY"].rolling(SMA_WINDOW).mean() if "SPY" in assets else None

    # Month-end rebalance dates (same pattern as risk_parity.py)
    month_end = pd.Series(True, index=px.index).groupby(
        [px.index.year, px.index.month]).tail(1).index

    me_weights = pd.DataFrame(0.0, index=month_end, columns=assets)

    for date in month_end:
        # Integer location for slice indexing (avoid get_loc ambiguity)
        pos = px.index.searchsorted(date, side="right") - 1
        if pos < cov_lookback:
            continue

        # Returns window up to and including month-end date
        window = ret.iloc[pos - cov_lookback: pos + 1].dropna(how="any")
        if len(window) < max(20, len(assets) + 1):
            continue

        # SMA gate: exclude SPY if below its 200-day average
        active = list(assets)
        if sma_gate and "SPY" in active and sma_spy is not None:
            spy_sma_val = sma_spy.iloc[pos] if not pd.isna(sma_spy.iloc[pos]) else None
            if spy_sma_val is not None and px.iloc[pos]["SPY"] < spy_sma_val:
                active = [a for a in active if a != "SPY"]

        if not active:
            continue

        sub = window[active]
        if sub.shape[1] == 0:
            continue

        cov = sub.cov().values  # daily covariance; annualization cancels in MinVar
        if np.any(np.isnan(cov)) or np.any(np.isinf(cov)):
            continue

        w = _min_var_weights(cov)
        for j, asset in enumerate(active):
            me_weights.loc[date, asset] = float(w[j])

    # Forward-fill monthly decisions to daily
    daily = me_weights.reindex(px.index).ffill().fillna(0.0)
    weights[assets] = daily[assets]

    # Safety: row sums must never exceed 1
    s = weights.sum(axis=1)
    over = s > 1.0
    if over.any():
        weights.loc[over] = weights.loc[over].div(s[over], axis=0)
    return weights
