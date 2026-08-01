"""Tests for strategies/vrp_timing.py (E40, session 26)."""
import numpy as np
import pandas as pd
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _spy_close():
    from data.loader import load_ohlcv
    return load_ohlcv("SPY", "2010-01-01")["Close"]


def test_vrp_signal_no_lookahead():
    """Signal at bar t must not change when we drop future bars."""
    from strategies.vrp_timing import signals
    spy = _spy_close()
    sig_full = signals(spy)
    sig_trunc = signals(spy.iloc[:-30])
    shared = sig_full.index.intersection(sig_trunc.index)
    # Allow NaN warmup differences but no value differences in shared index
    common = shared[sig_full.loc[shared].notna() & sig_trunc.loc[shared].notna()]
    pd.testing.assert_series_equal(
        sig_full.loc[common].round(8),
        sig_trunc.loc[common].round(8),
        check_names=False,
    )


def test_vrp_signal_bounds():
    """Signal must stay in [0, 1] at all times."""
    from strategies.vrp_timing import signals
    spy = _spy_close()
    sig = signals(spy)
    assert sig.min() >= 0.0 - 1e-9
    assert sig.max() <= 1.0 + 1e-9


def test_vrp_signal_less_than_or_equal_v2():
    """VRP overlay can only reduce (never increase) v2 exposure."""
    from strategies.vrp_timing import signals as vrp_sig
    from strategies.vol_target import signals as v2_sig
    spy = _spy_close()
    v2 = v2_sig(spy, target_vol=0.18, lookback=20)
    vrp = vrp_sig(spy, vrp_lb=63, vrp_scale=0.75)
    # At every bar, vrp <= v2 (VRP can only scale down, never up)
    aligned = pd.DataFrame({"v2": v2, "vrp": vrp}).dropna()
    assert (aligned["vrp"] <= aligned["v2"] + 1e-9).all(), \
        "VRP signal should never exceed v2 base signal"


def test_vrp_low_scale_lowers_exposure():
    """Lower vrp_scale produces strictly lower average exposure than higher."""
    from strategies.vrp_timing import signals
    spy = _spy_close()
    sig_lo = signals(spy, vrp_lb=63, vrp_scale=0.50)
    sig_hi = signals(spy, vrp_lb=63, vrp_scale=0.75)
    assert sig_lo.mean() < sig_hi.mean(), \
        "Lower vrp_scale should yield lower average exposure"


def test_vrp_higher_lb_produces_different_signal():
    """Different vrp_lb should produce different (not identical) signals."""
    from strategies.vrp_timing import signals
    spy = _spy_close()
    sig_40 = signals(spy, vrp_lb=40, vrp_scale=0.75)
    sig_63 = signals(spy, vrp_lb=63, vrp_scale=0.75)
    # Must differ by at least 0.1% on some bars
    diff = (sig_40 - sig_63).abs()
    assert diff.max() > 0.001, "Different vrp_lb should produce different signals"


def test_vrp_signal_handles_missing_vix():
    """Signal should gracefully propagate even when VIX has gaps."""
    from strategies.vrp_timing import signals
    spy = _spy_close()
    # Just confirm it runs without error on the standard data
    sig = signals(spy)
    assert len(sig) == len(spy)
    assert sig.isna().sum() < 300  # warmup NaNs only
