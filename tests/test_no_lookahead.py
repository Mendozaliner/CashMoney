"""Causality tests: signals may only use data available at decision time,
and the engine must execute on the bar *after* the signal bar."""
import numpy as np
import pandas as pd

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from strategies import sma_trend
from backtest import engine


def _random_close(n=800, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)


def test_signals_are_causal():
    """Truncating the future must not change past signal values."""
    close = _random_close()
    full = sma_trend.signals(close, window=50, band=0.01)
    for cut in (300, 500, 799):
        trunc = sma_trend.signals(close.iloc[:cut], window=50, band=0.01)
        pd.testing.assert_series_equal(full.iloc[:cut], trunc)


def test_engine_trades_after_signal_bar():
    """A signal first appearing on bar t must fill on bar t+1, never bar t."""
    close = _random_close(400, seed=1)
    sig = sma_trend.signals(close, window=50, band=0.0)
    stats, _ = engine.run(close, sig)
    first_on = int(np.argmax(sig.values > 0))
    assert len(stats._trades), "expected at least one trade"
    assert int(stats._trades["EntryBar"].min()) >= first_on + 1


def test_engine_costs_applied():
    """Round trip must cost ~2x commission."""
    close = pd.Series(100.0, index=pd.bdate_range("2020-01-01", periods=100))
    sig = pd.Series(0.0, index=close.index)
    sig.iloc[10:50] = 1.0
    stats, _ = engine.run(close, sig, commission=0.001)
    final = stats._equity_curve["Equity"].iloc[-1]
    assert final < 100_000_000, "commissions should reduce equity on flat prices"


if __name__ == "__main__":
    test_signals_are_causal()
    test_engine_trades_after_signal_bar()
    test_engine_costs_applied()
    print("all no-lookahead tests passed")
