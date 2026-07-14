"""Vector engine: timing cross-validation vs backtesting.py + no lookahead."""
import numpy as np
import pandas as pd

from backtest import engine, vector_engine
from data.loader import load_spy_proxy
from strategies import sma_trend, vol_target


def _close():
    return load_spy_proxy(start="2015-01-01", end="2022-12-31")["Close"]


def test_binary_signal_matches_backtesting_py():
    """Same binary signal through both engines -> near-identical results."""
    close = _close()
    sig = sma_trend.signals(close, 200, 0.03)
    m_bt = engine.metrics(close, sig)
    m_vec = vector_engine.metrics(close, sig)
    assert abs(m_bt["CAGR"] - m_vec["CAGR"]) < 0.35          # pct points
    assert abs(m_bt["Sharpe"] - m_vec["Sharpe"]) < 0.05
    assert abs(m_bt["MaxDD"] - m_vec["MaxDD"]) < 1.0


def test_no_lookahead_truncation_invariance():
    """Signals on truncated history equal signals on full history."""
    close = _close()
    full = vol_target.signals(close)
    cut = vol_target.signals(close.iloc[:-30])
    pd.testing.assert_series_equal(full.iloc[:-30], cut, check_names=False)


def test_position_lags_signal():
    """A signal turning on at t must not earn returns before t+2."""
    idx = pd.bdate_range("2020-01-01", periods=10)
    close = pd.Series(np.linspace(100, 110, 10), index=idx)
    sig = pd.Series(0.0, index=idx); sig.iloc[5:] = 1.0
    sr = vector_engine.strategy_returns(close, sig, commission=0.0)
    assert (sr.iloc[:7] == 0).all() and sr.iloc[7] > 0


def test_costs_charged_on_fractional_rebalance():
    idx = pd.bdate_range("2020-01-01", periods=10)
    close = pd.Series(100.0, index=idx)  # flat market: only costs remain
    sig = pd.Series([0, .5, .5, 1, 1, .25, .25, .25, .25, .25], index=idx,
                    dtype=float)
    sr = vector_engine.strategy_returns(close, sig, commission=0.001)
    assert np.isclose(-sr.sum(), 0.001 * (0.5 + 0.5 + 0.75))
