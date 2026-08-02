"""Causality and sanity tests for strategies/min_var.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from strategies import min_var as mv


def _panel(n=800, seed=42):
    idx = pd.bdate_range("2015-01-01", periods=n)
    rng = np.random.default_rng(seed)
    prices = {}
    vols = {"SPY": 0.012, "IEF": 0.004, "GLD": 0.009}
    for ticker, vol in vols.items():
        r = rng.normal(0.0003, vol, n)
        prices[ticker] = 100.0 * np.exp(np.cumsum(r))
    return pd.DataFrame(prices, index=idx)


def test_row_sums_bounded():
    """Weights must sum to <= 1 at every bar."""
    w = mv.multi_signals(_panel())
    s = w.sum(axis=1)
    assert (s <= 1.0 + 1e-9).all(), f"max row sum = {s.max()}"
    assert (s >= -1e-12).all()


def test_weights_non_negative():
    """Long-only constraint: no short positions."""
    w = mv.multi_signals(_panel())
    assert (w >= -1e-12).all(axis=None), "Negative weight detected"


def test_no_lookahead():
    """Perturbing future prices must not change past weights."""
    pan = _panel(n=900)
    w1 = mv.multi_signals(pan, cov_lookback=60)
    pan2 = pan.copy()
    pan2.iloc[-100:] *= 2.0  # violent future shock
    w2 = mv.multi_signals(pan2, cov_lookback=60)
    cutoff = pan.index[-120]
    pd.testing.assert_frame_equal(
        w1.loc[:cutoff], w2.loc[:cutoff],
        check_exact=False, rtol=1e-6,
    )


def test_sma_gate_excludes_spy_in_downtrend():
    """When SPY is below SMA200, sma_gate=True must zero out SPY weight."""
    pan = _panel(n=900)
    # Force SPY into a steep downtrend in the final 250 bars
    half = 650
    pan.iloc[half:, pan.columns.get_loc("SPY")] = (
        pan["SPY"].iloc[half] * np.exp(np.linspace(0, -0.8, 900 - half))
    )
    w = mv.multi_signals(pan, cov_lookback=60, sma_gate=True)
    # Last few month-end bars should have SPY weight = 0
    assert w["SPY"].iloc[-1] == 0.0, "SPY not zeroed in downtrend with sma_gate=True"


def test_sma_gate_false_allows_spy_in_downtrend():
    """When sma_gate=False, SPY can still receive weight even in downtrend."""
    pan = _panel(n=900)
    half = 650
    pan.iloc[half:, pan.columns.get_loc("SPY")] = (
        pan["SPY"].iloc[half] * np.exp(np.linspace(0, -0.8, 900 - half))
    )
    w = mv.multi_signals(pan, cov_lookback=60, sma_gate=False)
    # MinVar may still allocate to SPY when gate is off (weights can be > 0)
    # Just check row-sum constraint still holds
    s = w.sum(axis=1)
    assert (s <= 1.0 + 1e-9).all()


def test_insufficient_history_gives_zero():
    """With very short history, weights stay at zero until cov_lookback is met."""
    pan = _panel(n=300)
    w = mv.multi_signals(pan, cov_lookback=250)
    # First month-end before 250 days should be all zero
    first = w.loc[w.index[:50]].sum(axis=1)
    assert (first == 0.0).all()


def test_min_var_weights_analytical():
    """Unit test for the analytical weight computation."""
    # Identity covariance => equal weights
    cov = np.eye(3)
    w = mv._min_var_weights(cov)
    np.testing.assert_allclose(w, [1 / 3, 1 / 3, 1 / 3], atol=1e-9)


def test_min_var_weights_one_low_vol():
    """Asset with much lower variance should receive majority weight."""
    cov = np.diag([0.01, 0.0001, 0.01])  # IEF-like middle asset is 100x quieter
    w = mv._min_var_weights(cov)
    assert w[1] > 0.5, f"Low-vol asset weight too small: {w[1]:.4f}"


def test_single_asset_panel():
    """Works without crashing on a single-asset panel."""
    pan = _panel()[["SPY"]]
    w = mv.multi_signals(pan, assets=["SPY"])
    assert "SPY" in w.columns
