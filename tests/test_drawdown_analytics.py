"""Tests for tools/drawdown_analytics.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math
import numpy as np
import pandas as pd
import pytest
from tools.drawdown_analytics import (
    equity_curve,
    underwater_periods,
    drawdown_stats,
    semivariance,
    risk_of_ruin,
    ruin_surface,
    strategy_risk_report,
    UnderwaterPeriod,
)


def _bday_series(vals, start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(vals))
    return pd.Series(vals, index=idx)


def _flat(n=100, val=0.0):
    return _bday_series([val] * n)


def _sine(n=500, amplitude=0.02):
    vals = amplitude * np.sin(np.linspace(0, 4 * np.pi, n))
    return _bday_series(vals.tolist())


# ── equity_curve ──────────────────────────────────────────────────────────────

def test_equity_curve_flat():
    r = _flat(50, 0.0)
    eq = equity_curve(r, initial=1.0)
    assert len(eq) == 50
    np.testing.assert_allclose(eq.values, np.ones(50), atol=1e-12)


def test_equity_curve_constant_return():
    r = _flat(10, 0.01)
    eq = equity_curve(r, initial=100.0)
    expected = 100.0 * (1.01 ** 10)
    assert abs(float(eq.iloc[-1]) - expected) < 1e-6


def test_equity_curve_accepts_ndarray():
    arr = np.array([0.01, -0.02, 0.03])
    eq = equity_curve(arr)
    assert len(eq) == 3
    assert eq.iloc[0] == pytest.approx(1.01, abs=1e-9)


# ── underwater_periods ────────────────────────────────────────────────────────

def test_no_drawdown():
    r = _flat(50, 0.001)
    periods = underwater_periods(r)
    assert periods == []


def test_single_drawdown_detected():
    vals = [0.0] * 10 + [-0.05] * 5 + [0.06] + [0.0] * 10
    r = _bday_series(vals)
    periods = underwater_periods(r, threshold_pct=1.0)
    assert len(periods) == 1
    assert periods[0].depth_pct < -1.0


def test_open_drawdown_has_none_end():
    vals = [0.0] * 10 + [-0.02] * 20
    r = _bday_series(vals)
    periods = underwater_periods(r, threshold_pct=0.1)
    assert len(periods) >= 1
    assert periods[-1].end is None


def test_threshold_filters_shallow_dd():
    r = _sine(200)
    all_periods = underwater_periods(r, threshold_pct=0.0)
    deep_periods = underwater_periods(r, threshold_pct=50.0)
    assert len(all_periods) >= len(deep_periods)


# ── drawdown_stats ────────────────────────────────────────────────────────────

def test_drawdown_stats_all_positive():
    r = _flat(100, 0.001)
    stats = drawdown_stats(r)
    assert stats["n_drawdown_periods"] == 0
    assert stats["max_drawdown_pct"] == 0.0


def test_drawdown_stats_keys():
    r = _sine(400)
    stats = drawdown_stats(r)
    for key in ["n_drawdown_periods", "max_drawdown_pct", "avg_drawdown_pct",
                "avg_duration_days", "max_duration_days", "pct_time_underwater",
                "calmar_proxy"]:
        assert key in stats


def test_drawdown_stats_max_dd_negative():
    vals = [0.0] * 20 + [-0.03] * 30 + [0.04] + [0.0] * 10
    r = _bday_series(vals)
    stats = drawdown_stats(r)
    assert stats["max_drawdown_pct"] < 0.0


# ── semivariance ──────────────────────────────────────────────────────────────

def test_semivariance_all_positive():
    r = _flat(100, 0.01)
    sv = semivariance(r, threshold=0.0)
    assert sv == pytest.approx(0.0, abs=1e-12)


def test_semivariance_positive_value():
    rng = np.random.default_rng(42)
    r = rng.normal(0.0, 0.01, 1000)
    sv = semivariance(r, threshold=0.0, annualise=False)
    assert sv > 0.0  # must be strictly positive for a normal distribution


def test_semivariance_annualise():
    rng = np.random.default_rng(0)
    r = rng.normal(0.0, 0.01, 252)
    sv_ann = semivariance(r, annualise=True)
    sv_raw = semivariance(r, annualise=False)
    assert sv_ann == pytest.approx(sv_raw * math.sqrt(252), rel=1e-9)


def test_semivariance_higher_downside_vol():
    rng = np.random.default_rng(9)
    # Fat-tailed negative side: add large losses
    r = np.concatenate([rng.normal(0.002, 0.005, 800), rng.normal(-0.05, 0.02, 200)])
    sv_fat = semivariance(r, annualise=False)
    r_normal = rng.normal(0.001, 0.01, 1000)
    sv_norm = semivariance(r_normal, annualise=False)
    # Fat-tailed downside should have higher semivariance
    assert sv_fat > sv_norm


# ── risk_of_ruin ──────────────────────────────────────────────────────────────

def test_risk_of_ruin_zero_sigma():
    assert risk_of_ruin(0.10, 0.0) == 0.0


def test_risk_of_ruin_negative_drift():
    p = risk_of_ruin(-0.10, 0.15, ruin_threshold_pct=20.0, horizon_years=5.0)
    assert p > 0.5


def test_risk_of_ruin_high_drift_low_vol():
    p = risk_of_ruin(0.30, 0.05, ruin_threshold_pct=20.0, horizon_years=5.0)
    assert p < 0.01


def test_risk_of_ruin_range():
    for mu in [-0.05, 0.0, 0.10, 0.20]:
        p = risk_of_ruin(mu, 0.15, ruin_threshold_pct=15.0)
        assert 0.0 <= p <= 1.0


def test_risk_of_ruin_monotone_in_threshold():
    mu, sigma = 0.08, 0.15
    p_small = risk_of_ruin(mu, sigma, ruin_threshold_pct=10.0, horizon_years=5.0)
    p_large = risk_of_ruin(mu, sigma, ruin_threshold_pct=40.0, horizon_years=5.0)
    assert p_small >= p_large


# ── ruin_surface ──────────────────────────────────────────────────────────────

def test_ruin_surface_shape():
    df = ruin_surface(0.10, 0.15)
    assert df.shape == (5, 5)
    assert set(df.columns) == {"1yr", "3yr", "5yr", "10yr", "20yr"}


def test_ruin_surface_values_in_range():
    df = ruin_surface(0.10, 0.15)
    assert (df >= 0.0).all(axis=None)
    assert (df <= 100.0).all(axis=None)


# ── strategy_risk_report ──────────────────────────────────────────────────────

def test_strategy_risk_report_empty():
    r = strategy_risk_report(np.array([]), label="empty")
    assert r == {}


def test_strategy_risk_report_keys():
    r = _bday_series(list(np.random.default_rng(7).normal(0.0004, 0.012, 500)))
    report = strategy_risk_report(r, label="test")
    for key in ["label", "ann_return_pct", "ann_vol_pct", "semideviation_ann_pct",
                "sortino_proxy", "max_drawdown_pct", "risk_of_ruin_20pct_5yr"]:
        assert key in report
    assert report["label"] == "test"


def test_strategy_risk_report_dd_nonpositive():
    rng = np.random.default_rng(99)
    r = _bday_series(list(rng.normal(0.0, 0.015, 300)))
    report = strategy_risk_report(r)
    assert report["max_drawdown_pct"] <= 0.0
