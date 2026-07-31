"""Tests for strategies/inv_vol_gtaa.py (E38, session 25)."""
import numpy as np
import pandas as pd
import pytest

from strategies.inv_vol_gtaa import multi_signals


def _synthetic_prices(n=600, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-03", periods=n, freq="B")
    def _gbm(mu=0.08, sigma=0.18, s0=100.0):
        dt = 1 / 252
        r = rng.normal(mu * dt, sigma * np.sqrt(dt), n)
        return pd.Series(s0 * np.cumprod(1 + r), index=idx)
    return {
        "spy": _gbm(0.10, 0.18, 100.0),
        "ief": _gbm(0.04, 0.06, 100.0),
        "gld": _gbm(0.06, 0.16, 100.0),
        "vnq": _gbm(0.08, 0.20, 100.0),
    }


def test_weights_non_negative():
    p = _synthetic_prices()
    w = multi_signals(**p)
    assert (w >= 0).all().all()


def test_weights_sum_le_one():
    p = _synthetic_prices()
    w = multi_signals(**p)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()


def test_returns_dataframe_with_correct_columns():
    p = _synthetic_prices()
    w = multi_signals(**p)
    assert set(w.columns) == {"SPY", "IEF", "GLD", "VNQ"}


def test_no_lookahead_weights_are_zero_at_start():
    p = _synthetic_prices()
    w = multi_signals(**p, sma_window=200, vol_lookback=60)
    assert w.iloc[:60].sum(axis=1).sum() == 0.0, "Weights active before vol warmup"


def test_custom_params_respected():
    p = _synthetic_prices(n=700)
    w60  = multi_signals(**p, vol_lookback=60,  sma_window=150)
    w252 = multi_signals(**p, vol_lookback=252, sma_window=200)
    assert not w60.equals(w252), "Different params should produce different weights"


def test_month_end_rebalance_constant_intramonth():
    p = _synthetic_prices()
    w = multi_signals(**p)
    # Within each month (excluding the last day = rebalance day), weights are identical
    w_with_month = w.copy()
    w_with_month["_m"] = w.index.to_period("M")
    for _, grp in w_with_month.groupby("_m"):
        asset_cols = [c for c in grp.columns if c != "_m"]
        inner = grp[asset_cols].iloc[:-1]  # exclude month-end (rebalance day)
        if len(inner) > 1:
            first = inner.iloc[0]
            assert (inner == first).all().all(), (
                "Weights should be constant within each month (ex rebalance day)"
            )


def test_weights_zero_when_below_sma():
    n = 600
    idx = pd.date_range("2000-01-03", periods=n, freq="B")
    spy = pd.Series(np.linspace(110, 50, n), index=idx)   # strong downtrend
    ief = pd.Series(np.linspace(100, 90, n), index=idx)
    gld = pd.Series(np.linspace(100, 90, n), index=idx)
    vnq = pd.Series(np.linspace(100, 90, n), index=idx)
    w = multi_signals(spy, ief, gld, vnq, sma_window=200)
    late = w.iloc[250:]
    assert (late["SPY"] == 0).all(), "SPY in downtrend should have zero weight"
