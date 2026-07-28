"""Tests for corr_regime (E35) strategy — session 23."""
import numpy as np
import pandas as pd
import pytest

from strategies.corr_regime import multi_signals


def _prices(n=600, seed=42, drift=0.0003):
    rng = np.random.default_rng(seed)
    px = 100.0 * (1 + rng.normal(drift, 0.01, n)).cumprod()
    return pd.Series(px, index=pd.date_range("2002-01-01", periods=n, freq="B"))


def test_output_shape():
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    assert set(w.columns) == {"SPY", "IEF", "GLD"}
    assert len(w) == 600


def test_spy_weight_matches_v2():
    """SPY column must exactly equal v2 signal (equity sleeve unchanged)."""
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
    assert (w >= -1e-9).all().all()


def test_row_sum_leq_one():
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()


def test_not_simultaneously_ief_and_gld():
    """In any given period, at most one of IEF or GLD should be nonzero
    (regime switches between the two defensive assets)."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    both_nonzero = (w["IEF"].abs() > 1e-9) & (w["GLD"].abs() > 1e-9)
    assert not both_nonzero.any(), "IEF and GLD should not both be nonzero simultaneously"


def test_defensive_only_in_cash_periods():
    """IEF and GLD allocations are zero when SPY is fully invested."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld)
    fully_invested = w["SPY"].abs() >= 1.0 - 1e-9
    assert (w.loc[fully_invested, "IEF"].abs() < 1e-9).all()
    assert (w.loc[fully_invested, "GLD"].abs() < 1e-9).all()


def test_high_threshold_stays_in_ief():
    """With corr_threshold=1.0 (impossible to trigger), all defensive = IEF."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld, corr_threshold=1.0)
    assert (w["GLD"].abs() < 1e-9).all(), "threshold=1.0 → never inflation regime → GLD always 0"


def test_low_threshold_stays_in_gld():
    """With corr_threshold=-1.0 (always triggered), all defensive = GLD."""
    spy = _prices(600)
    ief = _prices(600, seed=1)
    gld = _prices(600, seed=2)
    w = multi_signals(spy, ief=ief, gld=gld, corr_threshold=-1.0)
    assert (w["IEF"].abs() < 1e-9).all(), "threshold=-1.0 → always inflation regime → IEF always 0"


def test_no_lookahead():
    """Earlier rows are unchanged when series is extended."""
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
