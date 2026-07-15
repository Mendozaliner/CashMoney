"""Causality and sanity tests for strategies/risk_parity.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from strategies import risk_parity as rp


def _panel(n=800, seed=7):
    idx = pd.bdate_range("2015-01-01", periods=n)
    rng = np.random.default_rng(seed)
    data = {}
    for i, t in enumerate(["SPY", "IEF", "GLD"]):
        r = rng.normal(0.0004, 0.008 * (i + 1) / 2, n)
        data[t] = 100 * np.exp(np.cumsum(r))
    return pd.DataFrame(data, index=idx)


def test_row_sums_bounded():
    w = rp.multi_signals(_panel())
    s = w.sum(axis=1)
    assert (s <= 1.0 + 1e-9).all() and (s >= -1e-12).all()


def test_no_lookahead():
    """Perturbing future prices must not change past weights."""
    pan = _panel()
    w1 = rp.multi_signals(pan, lookback=60, band=0.0)
    pan2 = pan.copy()
    pan2.iloc[-50:] *= 1.5  # violent future shock
    w2 = rp.multi_signals(pan2, lookback=60, band=0.0)
    cutoff = pan.index[-60]
    pd.testing.assert_frame_equal(w1.loc[:cutoff], w2.loc[:cutoff])


def test_gate_zeroes_downtrending_asset():
    pan = _panel()
    # Force GLD into a hard downtrend in the second half
    half = len(pan) // 2
    pan.iloc[half:, pan.columns.get_loc("GLD")] = (
        pan["GLD"].iloc[half] * np.exp(np.linspace(0, -1.0, len(pan) - half)))
    w = rp.multi_signals(pan, lookback=60, band=0.0)
    assert w["GLD"].iloc[-1] == 0.0


def test_insufficient_history_sits_in_cash():
    pan = _panel()
    pan.iloc[:600, pan.columns.get_loc("GLD")] = np.nan  # late-listing asset
    w = rp.multi_signals(pan, lookback=60, band=0.0)
    early = w.loc[w.index[250]]
    assert early["GLD"] == 0.0
    assert early.sum() < 1.0  # missing slot -> cash, not renormalized
