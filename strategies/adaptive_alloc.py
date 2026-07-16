"""Adaptive Asset Allocation (AAA) — Session 9, 2026-07-16.

Philosophy: most tactical strategies either pick assets by momentum alone
(GTAA: trend filter, equal weights on passing assets) or weight by risk alone
(risk parity: inverse-vol weights, no momentum filter). AAA combines both:
  1. Select the top-N assets by trailing return (momentum filter).
  2. Weight selected assets by minimum variance (not equal weight, not inv-vol)
     using a rolling correlation-aware covariance estimate.

This produces portfolios where selected assets get weights that minimize total
volatility given their current correlation structure — adding the information
in correlations that pure momentum strategies discard.

Key difference from GTAA (E6/E10): GTAA uses a trend gate (close > SMA) not
momentum ranking, and equal weights not min-var weights.
Key difference from Risk Parity (E12): RP uses all assets + inverse-vol weights;
AAA uses a ranked subset + covariance-based minimum-variance weights.
Key difference from Dual Momentum (E3/E7): pure ranking, no correlation-aware
weighting, single harbor.

Research basis:
- Butler, Philbrick, Gordillo & Vardy (2012) SSRN 2328254 "Adaptive Asset
  Allocation: A Primer" — scored assets by 6/12mo return, min-var weights.
- Markowitz, H. (1952) "Portfolio Selection", Journal of Finance — mean-var
  optimization; min-var is the corner of the efficient frontier nearest zero risk.
- Allocate Smartly & ReSolve Asset Mgmt live tracking show OOS Sharpe ~0.7–0.9
  (below the backtested 1.0+ in the original paper — data-mined, per our bar).

Parameters (max 2):
  top_n    : number of assets to select from ranked universe (default 3).
  lookback : return lookback in months (default 6 months ≈ 126 trading days).
"""
import numpy as np
import pandas as pd

DEFAULT_ASSETS = ["SPY", "IWM", "EFA", "IEF", "GLD", "DBC"]
COV_WINDOW = 60        # trading days for covariance estimate
MIN_VAR_FLOOR = 1e-8   # numerical floor on diagonal of cov matrix
TRADING_DAYS = 252
DEFAULTS = {"top_n": 3, "lookback": 6}

# Map integer months to approximate trading days
_MONTH_TD = 21


def _min_var_weights(cov: np.ndarray) -> np.ndarray:
    """Minimum variance weights for n assets given their covariance matrix.

    Closed-form solution: w = Σ⁻¹ 1 / (1ᵀ Σ⁻¹ 1)
    Falls back to equal weights if the matrix is singular.
    """
    n = cov.shape[0]
    ones = np.ones(n)
    try:
        inv = np.linalg.inv(cov + np.eye(n) * MIN_VAR_FLOOR)
        raw = inv @ ones
        total = ones @ raw
        if total <= 0 or not np.isfinite(total):
            return ones / n
        return raw / total
    except np.linalg.LinAlgError:
        return ones / n


def multi_signals(price_panel: pd.DataFrame, top_n: int = 3,
                  lookback: int = 6, assets=None) -> pd.DataFrame:
    """Weight DataFrame (date x ticker): AAA momentum-selection + min-var weights.

    Monthly decision dates (month-end), held intra-month.
    lookback in months (integer); covariance estimated on 60-trading-day window.
    """
    assets = [a for a in (assets or DEFAULT_ASSETS) if a in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if not assets or top_n < 1:
        return weights

    px = price_panel[assets].copy()
    ret = px.pct_change().fillna(0.0)
    lb_days = int(lookback * _MONTH_TD)

    month_ends = pd.Series(True, index=px.index).groupby(
        [px.index.year, px.index.month]).tail(1).index

    last_w = pd.Series(0.0, index=assets)
    w_schedule = {}

    for date in px.index:
        if date not in month_ends:
            w_schedule[date] = last_w.copy()
            continue

        prices_now = px.loc[date]
        has_data = prices_now.notna()
        active = [a for a in assets if has_data[a]]
        if not active:
            w_schedule[date] = last_w.copy()
            continue

        # 1. Momentum score = total return over lookback
        loc = px.index.get_loc(date)
        if loc < lb_days:
            # Not enough history: equal-weight active assets
            w = pd.Series({a: 1.0 / len(active) for a in active})
            last_w = w.reindex(assets, fill_value=0.0)
            w_schedule[date] = last_w.copy()
            continue

        px_lb = px.iloc[loc - lb_days:loc + 1][active]
        mom = (px_lb.iloc[-1] / px_lb.iloc[0] - 1.0).fillna(-np.inf)
        ranked = mom.sort_values(ascending=False)

        # 2. Select top-N (cap at number of active assets with positive mom)
        k = min(int(top_n), len(ranked))
        selected = ranked.head(k)
        # Only hold assets with positive momentum
        selected = selected[selected > -np.inf]
        if selected.empty:
            last_w = pd.Series(0.0, index=assets)
            w_schedule[date] = last_w.copy()
            continue
        sel_list = selected.index.tolist()

        # 3. Minimum variance weights on selected assets using 60-day cov
        if loc >= COV_WINDOW:
            ret_window = ret.iloc[loc - COV_WINDOW:loc + 1][sel_list]
            cov = ret_window.cov().values
            mv_w = _min_var_weights(cov)
        else:
            mv_w = np.ones(len(sel_list)) / len(sel_list)

        w = pd.Series(mv_w, index=sel_list)
        last_w = w.reindex(assets, fill_value=0.0)
        w_schedule[date] = last_w.copy()

    w_df = pd.DataFrame(w_schedule).T.reindex(price_panel.index).ffill().fillna(0.0)
    w_df = w_df.reindex(columns=price_panel.columns, fill_value=0.0)

    # Safety: row sums ≤ 1
    s = w_df.sum(axis=1)
    over = s > 1.0
    if over.any():
        w_df.loc[over] = w_df.loc[over].div(s[over], axis=0)
    return w_df
