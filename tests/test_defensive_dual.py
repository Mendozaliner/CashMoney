"""Tests for defensive_dual (E34) strategy — session 23."""
import numpy as np
import pandas as pd
import pytest

from strategies.defensive_dual import multi_signals


def _prices(n=600, seed=42):
    rng = np.random.default_rng(seed)
    px = 100.0 * (1 + rng.normal(0.0003, 0.01, n)).cumprod()
    return pd.Series(px, index=pd.date_range("2002-01-01", periods=n, freq="B"))


def test_output_shape():
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    assert set(w.columns) == {"SPY", "IEF", "GLD"}
    assert len(w) == 600


def test_spy_weight_matches_v2():
    """SPY column must exactly equal the v2 vol_target signal."""
    from strategies.vol_target import signals as vt_signals
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    v2 = vt_signals(spy, target_vol=0.18, lookback=20)
    pd.testing.assert_series_equal(w["SPY"], v2, check_names=False)


def test_weights_non_negative():
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    assert (w >= -1e-9).all().all(), "All weights must be non-negative"


def test_row_sum_leq_one():
    """Total allocation per row must not exceed 1.0 (no leverage)."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all(), "Row sums must be <= 1.0"


def test_gld_frac_zero_equals_ief_only():
    """With gld_frac=0, GLD column should always be 0."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld, gld_frac=0.0)
    assert (w["GLD"].abs() < 1e-9).all(), "gld_frac=0 → GLD always zero"


def test_gld_frac_one_equals_gld_only():
    """With gld_frac=1, IEF column should always be 0."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld, gld_frac=1.0)
    assert (w["IEF"].abs() < 1e-9).all(), "gld_frac=1.0 → IEF always zero"


def test_defensive_assets_only_in_cash_periods():
    """IEF and GLD allocations must be zero whenever SPY is fully invested."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    fully_invested = w["SPY"].abs() >= 1.0 - 1e-9
    assert (w.loc[fully_invested, "IEF"].abs() < 1e-9).all()
    assert (w.loc[fully_invested, "GLD"].abs() < 1e-9).all()


def test_no_lookahead():
    """Doubling series length changes only the tail, not earlier values."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w1 = multi_signals(spy.iloc[:400], ief.iloc[:400], gld.iloc[:400])
    w2 = multi_signals(spy, ief, gld)
    pd.testing.assert_frame_equal(
        w1.iloc[:350],
        w2.iloc[:350],
        check_names=False,
        rtol=1e-6,
    )
