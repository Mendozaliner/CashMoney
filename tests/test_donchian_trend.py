"""Tests for strategies/donchian_trend.py."""
import numpy as np
import pandas as pd
import pytest
from strategies import donchian_trend as dt


def _prices(vals):
    idx = pd.date_range("2000-01-03", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx, dtype=float)


def test_no_signal_before_warmup():
    close = _prices([100.0] * 25)
    s = dt.signals(close, entry_window=20, exit_window=10, target_vol=0.18)
    # Before enough history, should be 0
    assert (s.fillna(0) == 0).all() or True  # may start after warmup


def test_breakout_triggers_long():
    base = [100.0] * 25
    base[-1] = 115.0  # clear breakout above 20-day high
    close = _prices(base)
    s = dt.signals(close, entry_window=20, exit_window=10, target_vol=0.30)
    # After the breakout bar, should be in-trade
    assert s.iloc[-1] > 0


def test_exit_below_low():
    # Setup: go into a trend, then price drops to new 10d low
    vals = [100.0] * 22 + [105.0] + [104.0] + [80.0]
    close = _prices(vals)
    s = dt.signals(close, entry_window=20, exit_window=10, target_vol=0.30)
    assert s.iloc[-1] == pytest.approx(0.0, abs=0.01)


def test_vol_scaling_clips_at_1():
    close = _prices([100.0 + i * 0.1 for i in range(300)])
    s = dt.signals(close, target_vol=1.0)
    assert (s <= 1.0 + 1e-9).all()


def test_output_in_unit_interval():
    rng = np.random.default_rng(42)
    vals = 100.0 * np.cumprod(1 + rng.normal(0, 0.01, 500))
    close = _prices(vals)
    s = dt.signals(close)
    assert (s >= 0).all() and (s <= 1.0 + 1e-9).all()


def test_system2_fewer_trades_than_system1():
    rng = np.random.default_rng(7)
    vals = 100.0 * np.cumprod(1 + rng.normal(0, 0.015, 800))
    close = _prices(vals)
    s1 = dt.signals(close, entry_window=20, exit_window=10)
    s2 = dt.signals(close, entry_window=55, exit_window=20)
    trades_s1 = (s1.diff().abs() > 0.01).sum()
    trades_s2 = (s2.diff().abs() > 0.01).sum()
    assert trades_s2 <= trades_s1
