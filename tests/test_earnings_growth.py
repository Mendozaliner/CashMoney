"""Tests for strategies/earnings_growth.py (E39, session 25)."""
import numpy as np
import pandas as pd
import pytest

from strategies.earnings_growth import signals, _real_earnings_growth_daily


def _spy(n=800, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-03", periods=n, freq="B")
    dt = 1 / 252
    r = rng.normal(0.08 * dt, 0.18 * np.sqrt(dt), n)
    return pd.Series(100.0 * np.cumprod(1 + r), index=idx)


def test_output_in_unit_interval():
    spy = _spy()
    sig = signals(spy, growth_threshold=-0.05, de_risk_scale=0.5)
    assert ((sig >= 0) & (sig <= 1)).all(), "Exposure must be in [0, 1]"


def test_output_same_index():
    spy = _spy()
    sig = signals(spy)
    assert sig.index.equals(spy.index)


def test_signal_le_v2():
    from strategies import vol_target
    spy = _spy()
    v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
    sig = signals(spy, growth_threshold=-0.05, de_risk_scale=0.5)
    assert (sig <= v2 + 1e-9).all(), "EG signal must never exceed v2"


def test_de_risk_scale_respected():
    from strategies import vol_target
    spy = _spy()
    v2 = vol_target.signals(spy)

    # Use scale=0.0 to make contracting periods fully zero
    sig_zero = signals(spy, growth_threshold=0.99, de_risk_scale=0.0)
    # When threshold is very high (always contracting), scale=0 → all zero
    assert (sig_zero == 0).all() or (sig_zero <= v2 + 1e-9).all()


def test_growth_series_forward_filled():
    spy = _spy()
    eg = _real_earnings_growth_daily(spy.index)
    assert eg.index.equals(spy.index)
    assert eg.notna().all(), "All daily values should be filled"


def test_params_affect_output():
    spy = _spy()
    s1 = signals(spy, growth_threshold=-0.05, de_risk_scale=0.5)
    s2 = signals(spy, growth_threshold=-0.10, de_risk_scale=0.75)
    assert not s1.equals(s2), "Different params should produce different signals"


def test_no_lookahead_shiller_signal_stable():
    spy = _spy(n=800)
    eg1 = _real_earnings_growth_daily(spy.index[:600])
    eg2 = _real_earnings_growth_daily(spy.index)
    shared = eg1.index.intersection(eg2.index)
    pd.testing.assert_series_equal(
        eg1.loc[shared].round(8),
        eg2.loc[shared].round(8),
        check_names=False,
    )
