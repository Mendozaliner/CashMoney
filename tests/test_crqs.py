"""Tests for strategies/crqs.py (E42 Composite Regime-Quality Strategy)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from strategies.crqs import multi_signals


def _synthetic_shiller(n_months=300, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-01", periods=n_months, freq="ME")
    eps = 100.0 * np.exp(np.cumsum(rng.normal(0.002, 0.05, n_months)))
    cape = np.clip(rng.normal(25.0, 5.0, n_months), 10.0, 50.0)
    return pd.DataFrame({"CAPE": cape, "Earnings": eps}, index=idx)


def _prices(n=2000, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-01", periods=n)
    spy = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))), index=idx)
    ief = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.004, n))), index=idx)
    gld = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.009, n))), index=idx)
    return spy, ief, gld


def test_output_columns():
    spy, ief, gld = _prices()
    sh = _synthetic_shiller()
    w = multi_signals(spy, sh, ief=ief, gld=gld)
    assert set(w.columns) == {"SPY", "IEF", "GLD"}
    assert len(w) == len(spy)


def test_row_sums_bounded():
    """Weights must sum to at most 1 at every bar."""
    spy, ief, gld = _prices()
    sh = _synthetic_shiller()
    w = multi_signals(spy, sh, ief=ief, gld=gld)
    s = w.sum(axis=1)
    assert (s <= 1.0 + 1e-9).all(), f"max row sum = {s.max():.6f}"
    assert (s >= -1e-12).all()


def test_weights_non_negative():
    spy, ief, gld = _prices()
    sh = _synthetic_shiller()
    w = multi_signals(spy, sh, ief=ief, gld=gld)
    assert (w >= -1e-12).all(axis=None)


def test_no_lookahead():
    """Perturbing future prices must not change past weights."""
    spy, ief, gld = _prices(n=800)
    sh = _synthetic_shiller()
    w1 = multi_signals(spy, sh, ief=ief, gld=gld)

    spy2 = spy.copy()
    spy2.iloc[600:] *= 3.0
    w2 = multi_signals(spy2, sh, ief=ief, gld=gld)

    pd.testing.assert_frame_equal(
        w1.iloc[:599].round(10),
        w2.iloc[:599].round(10),
        check_names=False,
    )


def test_quality_gate_reduces_spy():
    """With a very high eps_threshold, the equity signal should be scaled down."""
    spy, ief, gld = _prices(n=1000)
    sh = _synthetic_shiller()

    w_no_gate = multi_signals(spy, sh, ief=ief, gld=gld, eps_threshold=-99.0)
    w_strict   = multi_signals(spy, sh, ief=ief, gld=gld, eps_threshold=+99.0,
                                scale_down=0.50)

    # When gate always fires (eps_threshold=+99 means always below), avg SPY < no-gate
    avg_no_gate = w_no_gate["SPY"].mean()
    avg_strict  = w_strict["SPY"].mean()
    assert avg_strict <= avg_no_gate + 0.01  # allow tiny float tolerance


def test_defensive_gld_increases_with_high_corr():
    """When stock-bond returns strongly co-move, GLD sleeve should activate."""
    n = 500
    idx = pd.bdate_range("2000-01-01", periods=n)
    rng = np.random.default_rng(7)
    # Bivariate with corr≈0.99 (not constant — avoids rolling-corr NaN)
    base = rng.normal(0.001, 0.01, n)
    noise = rng.normal(0.0, 0.001, n)
    spy = pd.Series(100.0 * np.exp(np.cumsum(base)), index=idx)
    ief = pd.Series(100.0 * np.exp(np.cumsum(base + noise)), index=idx)
    gld = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.009, n))), index=idx)
    sh = _synthetic_shiller(n_months=200)

    w = multi_signals(spy, sh, ief=ief, gld=gld,
                      corr_threshold=0.0, eps_threshold=-99.0)
    # After warm-up, GLD should often be non-zero (high positive corr → inflation regime)
    gld_engaged = (w["GLD"].iloc[100:] > 0).sum()
    assert gld_engaged > 0, "GLD sleeve never activated despite high stock-bond corr"


def test_different_params_differ():
    """Two configs with different eps_threshold should produce different weights."""
    spy, ief, gld = _prices()
    sh = _synthetic_shiller()
    w1 = multi_signals(spy, sh, ief=ief, gld=gld, eps_threshold=-0.05)
    w2 = multi_signals(spy, sh, ief=ief, gld=gld, eps_threshold=+0.05)
    assert not w1["SPY"].equals(w2["SPY"]), "Different params produced identical weights"


def test_scale_down_bounds_equity():
    """scale_down=0.5 should mean no equity weight exceeds 0.5 when gate fires."""
    spy, ief, gld = _prices(n=800)
    sh = _synthetic_shiller()
    w = multi_signals(spy, sh, ief=ief, gld=gld,
                      eps_threshold=+99.0,  # gate always fires
                      scale_down=0.50)
    # SPY weight ≤ 0.50 at all times (vol-target caps at 1.0, scaled to 0.5)
    assert (w["SPY"] <= 0.50 + 1e-9).all(), f"Max SPY = {w['SPY'].max():.4f}"
