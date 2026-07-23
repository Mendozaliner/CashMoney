"""Tests for strategies/fiftytwo_week.py."""
import numpy as np
import pandas as pd
import pytest
from strategies import fiftytwo_week as fw


def _prices(vals):
    idx = pd.date_range("2000-01-03", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx, dtype=float)


def test_at_peak_full_exposure():
    # Price at 52-week high → ratio = 1.0 > thresh_high → max exposure
    vals = [100.0] * 252 + [100.0]
    close = _prices(vals)
    s = fw.signals(close, thresh_high=0.90, thresh_low=0.80, target_vol=1.0)
    assert s.iloc[-1] == pytest.approx(1.0, abs=0.01)


def test_far_below_peak_zero_exposure():
    # Price at 70% of 52-week high → below thresh_low → 0 exposure
    vals = [100.0] * 252 + [70.0]
    close = _prices(vals)
    s = fw.signals(close, thresh_high=0.90, thresh_low=0.80, target_vol=1.0)
    assert s.iloc[-1] == pytest.approx(0.0, abs=0.01)


def test_linear_interpolation_between_thresholds():
    # Price at 85% of 52-week high, thresh_low=0.80, thresh_high=0.90
    # Expected raw = (0.85 - 0.80) / (0.90 - 0.80) = 0.5
    vals = [100.0] * 252 + [85.0]
    close = _prices(vals)
    s = fw.signals(close, thresh_high=0.90, thresh_low=0.80, target_vol=1.0)
    assert s.iloc[-1] == pytest.approx(0.5, abs=0.05)


def test_output_in_unit_interval():
    rng = np.random.default_rng(42)
    vals = 100.0 * np.cumprod(1 + rng.normal(0, 0.01, 500))
    close = _prices(vals)
    s = fw.signals(close)
    assert (s >= 0).all() and (s <= 1.0 + 1e-9).all()


def test_vol_scaling_reduces_exposure():
    # With target_vol=0.10 in a high-vol environment, exposure should be < 1
    rng = np.random.default_rng(1)
    vals = 100.0 * np.cumprod(1 + rng.normal(0, 0.03, 400))
    close = _prices(vals)
    s = fw.signals(close, thresh_high=0.90, thresh_low=0.80, target_vol=0.10)
    assert s.max() <= 1.0 + 1e-9
