"""Tests for tools/market_cycle.py — Howard Marks Market Cycle framework."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from tools.market_cycle import (
    valuation_score,
    fear_score,
    momentum_score,
    earnings_quality_score,
    equity_risk_premium_score,
    composite_cycle_score,
    cycle_summary,
)

BDAYS = pd.bdate_range("2000-01-01", periods=6000)


def _make_shiller(n=400, cape_val=20.0, eps_val=150.0, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    df = pd.DataFrame({
        "CAPE": cape_val * (1 + rng.normal(0, 0.02, n)).clip(0.5),
        "Earnings": eps_val * (1 + rng.normal(0.002, 0.01, n)).cumprod(),
        "Rate GS10": 3.0 + rng.normal(0, 0.2, n),
    }, index=idx)
    return df


def _make_vix(n=6000, level=15.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-01", periods=n)
    return pd.Series(level * np.exp(rng.normal(0, 0.1, n)), index=idx)


def _make_spy(n=6000, drift=0.0003, vol=0.012, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-01", periods=n)
    return pd.Series(100.0 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)


def _make_ief(n=6000, seed=2):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-01", periods=n)
    return pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.003, n))), index=idx)


def _rf_daily(n=6000):
    idx = pd.bdate_range("2000-01-01", periods=n)
    return pd.Series(0.04 / 252, index=idx)


def _cycle_df():
    sh = _make_shiller()
    spy = _make_spy()
    ief = _make_ief()
    vix = _make_vix()
    rf = _rf_daily()
    return composite_cycle_score(sh, spy, ief, vix, rf)


# ── valuation_score ───────────────────────────────────────────────────────────

def test_valuation_score_returns_series():
    sh = _make_shiller()
    score = valuation_score(sh, BDAYS)
    assert isinstance(score, pd.Series)
    assert len(score) == len(BDAYS)


def test_valuation_score_range():
    sh = _make_shiller()
    score = valuation_score(sh, BDAYS).dropna()
    assert (score >= 0.0).all() and (score <= 1.0).all()


def test_valuation_score_recent_spike_scores_high():
    """A CAPE spike period should score higher than the low-CAPE baseline."""
    rng = np.random.default_rng(42)
    n = 250
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    spike_start = n - 30  # months 220-249 are the spike
    cape_vals = np.concatenate([
        rng.uniform(8, 12, spike_start),   # historically low CAPE
        rng.uniform(40, 50, 30),            # sudden spike to extreme highs
    ])
    sh = pd.DataFrame({"CAPE": cape_vals, "Earnings": 100.0, "Rate GS10": 3.0}, index=idx)
    # Use a daily index that spans the full shiller range so the spike is visible
    bdays = pd.bdate_range(idx[0], idx[-1])
    score = valuation_score(sh, bdays).dropna()
    mid = len(score) * spike_start // n
    cheap_mean = float(score.iloc[252:mid].mean())   # skip warm-up artifact
    spike_mean = float(score.iloc[mid:].mean())
    assert spike_mean > cheap_mean + 0.15


# ── fear_score ────────────────────────────────────────────────────────────────

def test_fear_score_range():
    vix = _make_vix()
    score = fear_score(vix).dropna()
    assert (score >= 0.0).all() and (score <= 1.0).all()


def test_fear_score_last_point_low_vix():
    """Series ending with a low VIX period should have fear_score near 1 (complacency)."""
    n = 1500
    idx = pd.bdate_range("2015-01-01", periods=n)
    # Construct: mostly high VIX, then suddenly very low
    vals = [40.0] * (n - 100) + [5.0] * 100
    vix = pd.Series(vals, index=idx)
    score = fear_score(vix)
    assert float(score.iloc[-1]) > 0.5  # low VIX end → high complacency score


# ── momentum_score ────────────────────────────────────────────────────────────

def test_momentum_score_range():
    spy = _make_spy()
    score = momentum_score(spy).dropna()
    assert (score >= 0.0).all() and (score <= 1.0).all()


def test_momentum_score_uptrending_vs_downtrending():
    n = 3000
    idx = pd.bdate_range("2010-01-01", periods=n)
    up   = pd.Series(100.0 * np.exp(np.linspace(0, 2.0, n)), index=idx)
    down = pd.Series(100.0 * np.exp(np.linspace(0, -1.0, n)), index=idx)
    assert float(momentum_score(up).dropna().mean()) > float(momentum_score(down).dropna().mean())


# ── earnings_quality_score ────────────────────────────────────────────────────

def test_eps_quality_score_range():
    sh = _make_shiller()
    score = earnings_quality_score(sh, BDAYS).dropna()
    assert (score >= 0.0).all() and (score <= 1.0).all()


def test_eps_quality_score_returns_series():
    sh = _make_shiller()
    score = earnings_quality_score(sh, BDAYS)
    assert isinstance(score, pd.Series)


# ── equity_risk_premium_score ─────────────────────────────────────────────────

def test_erp_score_range():
    sh = _make_shiller()
    rf = _rf_daily()
    score = equity_risk_premium_score(sh, rf, BDAYS).dropna()
    assert (score >= 0.0).all() and (score <= 1.0).all()


def test_erp_score_spike_raises_risk():
    """CAPE surge → earnings yield crashes → ERP falls → risk score rises."""
    rng = np.random.default_rng(5)
    n = 250
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    spike_start = n - 30  # months 220-249 are the spike
    cape_vals = np.concatenate([
        rng.uniform(8, 15, spike_start),   # long history of cheap market
        rng.uniform(45, 60, 30),            # spike to extreme richness
    ])
    sh = pd.DataFrame({"CAPE": cape_vals, "Earnings": 100.0, "Rate GS10": 3.0}, index=idx)
    # Use a local rf aligned to the shiller-spanning daily index
    bdays = pd.bdate_range(idx[0], idx[-1])
    rf = pd.Series(0.04 / 252, index=bdays)
    score = equity_risk_premium_score(sh, rf, bdays).dropna()
    mid = len(score) * spike_start // n
    cheap_mean = float(score.iloc[252:mid].mean())   # skip warm-up artifact
    spike_mean = float(score.iloc[mid:].mean())
    assert spike_mean > cheap_mean + 0.15


# ── composite_cycle_score ─────────────────────────────────────────────────────

def test_composite_cycle_score_columns():
    df = _cycle_df()
    for col in ["cycle_score", "valuation", "fear", "momentum", "eps_quality", "erp"]:
        assert col in df.columns


def test_composite_cycle_score_range():
    df = _cycle_df()
    scores = df["cycle_score"].dropna()
    assert (scores >= 0.0).all() and (scores <= 1.0).all()


def test_composite_cycle_score_length():
    df = _cycle_df()
    assert len(df) > 0
    assert len(df) == 6000  # aligned to spy.index


# ── cycle_summary ─────────────────────────────────────────────────────────────

def test_cycle_summary_returns_dict():
    df = _cycle_df()
    result = cycle_summary(df)
    assert isinstance(result, dict)
    assert "current_score" in result or "cycle_score" in result


def test_cycle_summary_label_in_valid_set():
    df = _cycle_df()
    result = cycle_summary(df)
    label_key = "cycle_label" if "cycle_label" in result else "label"
    if label_key in result:
        valid = {"early_cycle_opportunity", "mid_cycle_neutral", "late_cycle_risk",
                 "peak_risk", "early_mid_cycle", "mid_late_cycle"}
        assert result[label_key] in valid


def test_cycle_summary_score_in_range():
    df = _cycle_df()
    result = cycle_summary(df)
    score_key = "current_score" if "current_score" in result else "cycle_score"
    if score_key in result:
        assert 0.0 <= result[score_key] <= 1.0
