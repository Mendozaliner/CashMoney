"""Tests for strategies/adx_trend.py."""
import numpy as np
import pandas as pd
import pytest
from strategies import adx_trend as adx_mod


def _close(vals):
    idx = pd.date_range("2000-01-03", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx, dtype=float)


def test_adx_nonnegative():
    rng = np.random.default_rng(42)
    c = _close(100 * np.cumprod(1 + rng.normal(0, 0.01, 300)))
    s = adx_mod.signals(c)
    assert (s >= 0).all()


def test_output_in_unit_interval():
    rng = np.random.default_rng(7)
    c = _close(100 * np.cumprod(1 + rng.normal(0, 0.01, 500)))
    s = adx_mod.signals(c)
    assert (s <= 1.0 + 1e-9).all()


def test_low_threshold_more_exposure_than_high():
    rng = np.random.default_rng(13)
    c = _close(100 * np.cumprod(1 + rng.normal(0, 0.008, 600)))
    s_low = adx_mod.signals(c, adx_period=14, adx_threshold=10)
    s_high = adx_mod.signals(c, adx_period=14, adx_threshold=30)
    # Lower threshold → more of the time ADX >= threshold → higher avg exposure
    assert s_low.mean() >= s_high.mean()


def test_trend_off_when_adx_zero():
    # Flat price → ADX should be near zero → exposure should be 0
    close = _close([100.0] * 250)
    s = adx_mod.signals(close, adx_period=14, adx_threshold=20)
    assert (s <= 1e-6).all()


def test_trend_gate_respected():
    # Prices below SMA200 should yield zero exposure regardless of ADX
    vals = [200.0] * 200 + [100.0] * 150  # sharp drop below SMA200
    close = _close(vals)
    s = adx_mod.signals(close, adx_threshold=0)  # any ADX allowed
    assert s.iloc[-1] == pytest.approx(0.0, abs=0.01)
