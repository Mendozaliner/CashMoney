"""Tests for tools/regime_detector.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from tools.regime_detector import (
    detect_regime, regime_weights, regime_summary, REGIMES,
)


def _synthetic_shiller(n_months=300, seed=42):
    """Minimal Shiller-like monthly DataFrame."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-01", periods=n_months, freq="ME")
    eps = 100.0 * np.exp(np.cumsum(rng.normal(0.002, 0.05, n_months)))
    cape = np.clip(rng.normal(25.0, 5.0, n_months), 10.0, 50.0)
    return pd.DataFrame({"CAPE": cape, "Earnings": eps}, index=idx)


def _prices(n=2000, spy_vol=0.012, ief_vol=0.004, corr=-0.3, seed=42):
    """Synthetic SPY and IEF daily close series."""
    rng = np.random.default_rng(seed)
    cov = [[spy_vol**2, corr*spy_vol*ief_vol],
           [corr*spy_vol*ief_vol, ief_vol**2]]
    r = rng.multivariate_normal([0.0003, 0.0001], cov, n)
    idx = pd.bdate_range("2000-01-01", periods=n)
    spy = pd.Series(100.0 * np.exp(np.cumsum(r[:, 0])), index=idx)
    ief = pd.Series(100.0 * np.exp(np.cumsum(r[:, 1])), index=idx)
    return spy, ief


def test_output_shape_and_columns():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    assert set(df.columns) == {"regime", "growth_up", "inflation", "eps_growth", "sb_corr"}
    assert len(df) == len(spy)


def test_regimes_are_valid_labels():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    assert set(df["regime"].unique()).issubset(set(REGIMES))


def test_no_lookahead_regime():
    """Perturbing future prices must not change past regime labels."""
    spy, ief = _prices(n=600)
    sh = _synthetic_shiller()
    df1 = detect_regime(sh, spy, ief)

    spy2 = spy.copy()
    spy2.iloc[400:] *= 2.0  # large future shock
    df2 = detect_regime(sh, spy2, ief)

    # Past (first 399 rows) must be identical
    pd.testing.assert_series_equal(
        df1["regime"].iloc[:399],
        df2["regime"].iloc[:399],
        check_names=False,
    )


def test_regime_logic_inflating_corr():
    """When stock-bond returns are strongly positively correlated, inflation flag should be True."""
    n = 400
    idx = pd.bdate_range("2000-01-01", periods=n)
    rng = np.random.default_rng(7)
    # Use bivariate normal with corr=0.99 so returns vary (avoiding zero-variance NaN issue)
    base = rng.normal(0.001, 0.01, n)
    noise = rng.normal(0.0, 0.001, n)
    spy = pd.Series(100.0 * np.exp(np.cumsum(base)), index=idx)
    ief = pd.Series(100.0 * np.exp(np.cumsum(base + noise)), index=idx)

    sh = _synthetic_shiller(n_months=200)
    df = detect_regime(sh, spy, ief, corr_threshold=0.0, corr_lookback=30)
    # After warm-up (50+ days), most days should be inflation (corr ≈ 0.99 > 0.0)
    inflation_rate = df["inflation"].iloc[50:].mean()
    assert inflation_rate > 0.80, f"Inflation detection rate too low: {inflation_rate:.2f}"


def test_regime_weights_keys():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    w = regime_weights(df["regime"])
    assert set(w.columns) == {"SPY", "IEF", "GLD"}
    assert len(w) == len(df)


def test_regime_weights_sum_to_one():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    w = regime_weights(df["regime"])
    row_sums = w.sum(axis=1)
    assert (row_sums - 1.0).abs().max() < 1e-10


def test_regime_summary_keys():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    s = regime_summary(df)
    assert "total_days" in s
    assert "regime_pct" in s
    assert set(s["regime_pct"].keys()) == set(REGIMES)


def test_regime_summary_pct_sums_to_100():
    spy, ief = _prices()
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    s = regime_summary(df)
    total = sum(s["regime_pct"].values())
    assert abs(total - 100.0) < 0.2  # rounding tolerance


def test_regime_summary_date_slice():
    spy, ief = _prices(n=1000)
    sh = _synthetic_shiller()
    df = detect_regime(sh, spy, ief)
    s_full = regime_summary(df)
    s_slice = regime_summary(df, start="2001-01-01", end="2002-01-01")
    assert s_slice["total_days"] < s_full["total_days"]
