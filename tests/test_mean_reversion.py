"""No-lookahead + sanity tests for strategies/mean_reversion.py (s11)."""
import numpy as np
import pandas as pd
import pytest
from strategies import mean_reversion as mr


def _fake_ohlc(n=600, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n))), idx)
    h = c * (1 + rng.uniform(0, 0.01, n))
    l = c * (1 - rng.uniform(0, 0.01, n))
    return pd.DataFrame({"Close": c, "High": h, "Low": l})


@pytest.mark.parametrize("fn,args", [
    ("rsi2", (10.0, 70.0)), ("boll", (2.0, "mid")), ("ibs", (0.2, 0.8))])
def test_no_lookahead(fn, args):
    df = _fake_ohlc()
    def sig(d):
        if fn == "rsi2":
            return mr.rsi2_signals(d["Close"], *args)
        if fn == "boll":
            return mr.bollinger_signals(d["Close"], *args)
        return mr.ibs_signals(d, *args)
    full = sig(df)
    trunc = sig(df.iloc[:-50])
    # Signals must be identical on the shared history
    pd.testing.assert_series_equal(full.iloc[:-50], trunc, check_names=False)


def test_binary_and_gated():
    df = _fake_ohlc()
    for s in (mr.rsi2_signals(df["Close"]), mr.bollinger_signals(df["Close"]),
              mr.ibs_signals(df)):
        assert set(np.unique(s)) <= {0.0, 1.0}
    # bear market: monotonic decline -> gate off -> never long after warmup
    dn = pd.Series(np.linspace(100, 40, 400), pd.bdate_range("2015-01-01", periods=400))
    s = mr.rsi2_signals(dn, 10, 70)
    assert s.iloc[220:].sum() == 0


def test_rsi_bounds():
    df = _fake_ohlc()
    r = mr._rsi(df["Close"], 2)
    assert r.min() >= 0 and r.max() <= 100
