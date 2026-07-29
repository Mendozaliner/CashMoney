"""Tests for swensen_alloc (E37) strategy — session 24."""
import numpy as np
import pandas as pd
import pytest

from strategies.swensen_alloc import multi_signals, EQUITY_WEIGHT, BOND_WEIGHT, GOLD_WEIGHT, REAL_WEIGHT


def _series(n=600, seed=42):
    rng = np.random.default_rng(seed)
    px = 100.0 * (1 + rng.normal(0.0003, 0.01, n)).cumprod()
    return pd.Series(px, index=pd.date_range("2002-01-01", periods=n, freq="B"))


def test_vnq_output_columns():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq, use_dbc=False)
    assert set(w.columns) == {"SPY", "IEF", "GLD", "VNQ"}


def test_dbc_output_columns():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    dbc = _series(600, seed=4)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=dbc, use_dbc=True)
    assert set(w.columns) == {"SPY", "IEF", "GLD", "DBC"}


def test_output_length():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq)
    assert len(w) == 600


def test_weights_non_negative():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq)
    assert (w >= -1e-9).all().all()


def test_row_sum_leq_one():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()


def test_equal_slot_weights():
    """Each asset's max possible allocation is exactly 0.25."""
    assert EQUITY_WEIGHT == BOND_WEIGHT == GOLD_WEIGHT == REAL_WEIGHT == 0.25


def test_spy_max_weight():
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq)
    assert w["SPY"].max() <= 0.25 + 1e-9


def test_no_lookahead():
    """Truncating the series at 400 must not change rows up to 350."""
    spy = _series(600)
    ief = _series(600, seed=1)
    gld = _series(600, seed=2)
    vnq = _series(600, seed=3)
    w1 = multi_signals(spy.iloc[:400], ief.iloc[:400], gld.iloc[:400], vnq.iloc[:400])
    w2 = multi_signals(spy, ief, gld, vnq)
    pd.testing.assert_frame_equal(
        w1.iloc[:350],
        w2.iloc[:350],
        check_names=False,
        rtol=1e-6,
    )


def test_sma_window_larger_than_series_zeros():
    """Window > series length → all weights 0."""
    spy = _series(50)
    ief = _series(50, seed=1)
    gld = _series(50, seed=2)
    vnq = _series(50, seed=3)
    w = multi_signals(spy, ief=ief, gld=gld, real_asset=vnq, sma_window=300)
    assert (w.abs() < 1e-9).all().all()
