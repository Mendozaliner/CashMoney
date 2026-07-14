"""Causality + construction tests for strategies/gtaa.py (session 6)."""
import numpy as np
import pandas as pd
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from strategies import gtaa


def _panel(n=900, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    data = {t: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
            for t in ["SPY", "IWM", "IEF", "GLD"]}
    return pd.DataFrame(data, index=idx)


def test_no_lookahead():
    """Changing future prices must not change past weights."""
    pan = _panel()
    w1 = gtaa.multi_signals(pan, window=200, band=0.0)
    pan2 = pan.copy()
    pan2.iloc[-100:] *= 3.0  # violent future move
    w2 = gtaa.multi_signals(pan2, window=200, band=0.0)
    cut = pan.index[-101]
    pd.testing.assert_frame_equal(w1.loc[:cut], w2.loc[:cut])


def test_weights_are_fixed_slots():
    pan = _panel()
    w = gtaa.multi_signals(pan, window=150, band=0.03)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()
    vals = np.unique(w.values)
    assert set(np.round(vals, 6)) <= {0.0, 0.25}


def test_monthly_holding():
    """Weights only change at month boundaries (first bar after month-end)."""
    pan = _panel()
    w = gtaa.multi_signals(pan, window=200, band=0.0)
    chg = w.diff().abs().sum(axis=1)
    changes = chg[chg > 0].index
    # signal rows change ON the month-end decision bar (engine executes t+1)
    month_ends = w.index.to_series().groupby(
        [w.index.year, w.index.month]).tail(1).index
    for d in changes:
        assert d in month_ends
