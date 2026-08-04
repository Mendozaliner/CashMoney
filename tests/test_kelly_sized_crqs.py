"""Tests for strategies/kelly_sized_crqs.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from strategies.kelly_sized_crqs import multi_signals, VOL_TARGET_GRID, BEST_CRQS_PARAMS


def _spy(n=2000, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.Series(400.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))), index=idx)


def _shiller(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="MS")
    return pd.DataFrame({
        "CAPE": 25 + rng.normal(0, 2, n),
        "Earnings": 150.0 * (1 + rng.normal(0.002, 0.01, n)).cumprod(),
        "Rate GS10": 3 + rng.normal(0, 0.2, n),
    }, index=idx)


def _ief_gld(spy):
    idx = spy.index
    ief = pd.Series(110.0, index=idx)
    gld = pd.Series(180.0, index=idx)
    return ief, gld


def test_vol_target_grid_contents():
    assert 0.18 in VOL_TARGET_GRID
    assert len(VOL_TARGET_GRID) == 6
    assert all(vt > 0 for vt in VOL_TARGET_GRID)


def test_best_crqs_params_keys():
    for key in ["eps_threshold", "scale_down", "corr_threshold", "corr_lb"]:
        assert key in BEST_CRQS_PARAMS


def test_output_shape():
    spy = _spy()
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    w = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=0.18)
    assert set(w.columns) >= {"SPY", "IEF", "GLD"}
    assert len(w) == len(spy)


def test_weights_non_negative():
    spy = _spy()
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    for vt in [0.09, 0.18, 0.24]:
        w = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=vt)
        assert (w >= -1e-10).all(axis=None), f"Negative weight at vol_target={vt}"


def test_row_sum_bounded():
    spy = _spy()
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    for vt in VOL_TARGET_GRID:
        w = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=vt)
        row_sum = w.sum(axis=1)
        assert (row_sum <= 1.0 + 1e-9).all(), f"Row sum > 1 at vol_target={vt}"


def test_lower_vol_target_reduces_spy_avg():
    spy = _spy()
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    w_low = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=0.09)
    w_high = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=0.24)
    # On average, lower vol_target should produce lower or equal average SPY weight
    avg_low = float(w_low["SPY"].mean())
    avg_high = float(w_high["SPY"].mean())
    assert avg_low <= avg_high + 0.05  # allow small tolerance


def test_default_vol_target_matches_champion():
    spy = _spy()
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    w_default = multi_signals(spy, sh, ief=ief, gld=gld)
    w_018 = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=0.18)
    pd.testing.assert_frame_equal(w_default, w_018)


def test_no_lookahead():
    spy = _spy(n=1500)
    sh = _shiller()
    ief, gld = _ief_gld(spy)
    w1 = multi_signals(spy, sh, ief=ief, gld=gld, vol_target=0.18)
    spy2 = spy.copy()
    spy2.iloc[-200:] *= 2.0
    w2 = multi_signals(spy2, sh, ief=ief, gld=gld, vol_target=0.18)
    cutoff = spy.index[-250]
    pd.testing.assert_frame_equal(w1.loc[:cutoff], w2.loc[:cutoff],
                                  check_exact=False, rtol=1e-6)
