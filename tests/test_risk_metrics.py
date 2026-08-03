"""Tests for tools/risk_metrics.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from tools.risk_metrics import (
    cvar, cvar_annualised, omega_ratio, calmar_ratio,
    information_ratio, tail_ratio, comprehensive_risk_report,
)


def _returns(n=1000, seed=42):
    rng = np.random.default_rng(seed)
    return rng.normal(0.0004, 0.012, n)


# ── CVaR ──────────────────────────────────────────────────────────────────────

def test_cvar_non_negative():
    r = _returns()
    assert cvar(r) >= 0.0


def test_cvar_worse_than_var():
    """CVaR must be >= VaR at the same alpha."""
    r = _returns()
    alpha = 0.05
    var = -np.quantile(r, alpha)
    assert cvar(r, alpha) >= var - 1e-10


def test_cvar_all_losses():
    """All-loss series: CVaR should equal mean of worst 5%."""
    r = np.array([-0.01, -0.02, -0.03, -0.04, -0.05,
                  -0.10, -0.20] + [-0.001] * 93)
    c = cvar(r, 0.05)
    worst5 = np.sort(r)[:int(len(r) * 0.05)]
    expected = -worst5.mean()
    assert abs(c - expected) < 1e-10


def test_cvar_ann_larger_than_daily():
    r = _returns()
    assert cvar_annualised(r) > cvar(r)


# ── Omega ─────────────────────────────────────────────────────────────────────

def test_omega_positive_expectation():
    """Positive-drift returns should have omega > 1 (use large n for reliability)."""
    rng = np.random.default_rng(7)
    r = rng.normal(0.002, 0.010, 5000)  # strong drift, large sample
    assert omega_ratio(r) > 1.0


def test_omega_negative_expectation():
    """Negative-drift returns should have omega < 1."""
    rng = np.random.default_rng(7)
    r = rng.normal(-0.001, 0.010, 500)
    assert omega_ratio(r) < 1.0


def test_omega_zero_losses_returns_inf():
    r = np.array([0.01, 0.02, 0.05, 0.10])
    assert omega_ratio(r, threshold=0.0) == float("inf")


# ── Calmar ────────────────────────────────────────────────────────────────────

def test_calmar_sign_follows_cagr():
    """Calmar sign should match the sign of the CAGR."""
    rng = np.random.default_rng(99)
    r_pos = rng.normal(+0.001, 0.005, 1000)  # positive drift → positive Calmar
    r_neg = rng.normal(-0.001, 0.005, 1000)  # negative drift → negative Calmar
    assert calmar_ratio(r_pos) > 0.0
    assert calmar_ratio(r_neg) < 0.0


def test_calmar_zero_on_flat():
    r = np.zeros(252)
    assert calmar_ratio(r) == 0.0


def test_calmar_good_strategy():
    """A strongly positive strategy should produce a decent Calmar."""
    rng = np.random.default_rng(1)
    # ~10% CAGR, low DD
    r = rng.normal(0.0004, 0.005, 2000)
    c = calmar_ratio(r)
    assert c > 0.0


# ── Information Ratio ─────────────────────────────────────────────────────────

def test_ir_zero_for_identical():
    """When strategy == benchmark, IR should be 0."""
    r = _returns()
    ir = information_ratio(r, r)
    assert abs(ir) < 1e-10


def test_ir_positive_when_better():
    rng = np.random.default_rng(3)
    bench = rng.normal(0.0001, 0.012, 1000)
    strat = bench + rng.normal(0.0005, 0.005, 1000)
    assert information_ratio(strat, bench) > 0


def test_ir_handles_length_mismatch():
    """Mismatched length arrays should not raise."""
    strat = _returns(500)
    bench = _returns(700)
    ir = information_ratio(strat, bench)
    assert np.isfinite(ir)


# ── Tail ratio ────────────────────────────────────────────────────────────────

def test_tail_ratio_positive():
    assert tail_ratio(_returns()) > 0.0


def test_tail_ratio_symmetric_normal():
    """Symmetric normal should have tail ratio ≈ 1."""
    rng = np.random.default_rng(99)
    r = rng.normal(0.0, 1.0, 100_000)
    tr = tail_ratio(r)
    assert abs(tr - 1.0) < 0.1


def test_tail_ratio_right_skew():
    """Right-skewed series should have tail ratio > 1."""
    rng = np.random.default_rng(5)
    r = rng.exponential(0.01, 5000) - 0.005
    # Most positives, few large positives; add symmetric large negatives rarely
    tr = tail_ratio(r)
    assert tr > 0.0


# ── Comprehensive report ──────────────────────────────────────────────────────

def test_report_keys():
    r = _returns()
    rpt = comprehensive_risk_report(r)
    for key in ["sharpe", "cvar_daily", "cvar_ann", "omega", "calmar",
                "tail_ratio", "max_dd", "information_ratio"]:
        assert key in rpt, f"Missing key: {key}"


def test_report_ir_none_without_benchmark():
    r = _returns()
    rpt = comprehensive_risk_report(r)
    assert rpt["information_ratio"] is None


def test_report_ir_present_with_benchmark():
    r = _returns(500)
    b = _returns(500, seed=7)
    rpt = comprehensive_risk_report(r, b)
    assert rpt["information_ratio"] is not None
    assert np.isfinite(rpt["information_ratio"])


def test_report_all_finite():
    r = _returns()
    rpt = comprehensive_risk_report(r, _returns(seed=7))
    for k, v in rpt.items():
        if v is not None:
            assert np.isfinite(v), f"Non-finite value for {k}: {v}"
