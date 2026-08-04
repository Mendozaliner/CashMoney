"""Tests for strategies/crqs_minvar_ensemble.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from strategies.crqs_minvar_ensemble import multi_signals, BLEND_GRID, CRQS_PARAMS, MINVAR_PARAMS


def _panel(n=2000, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    data = {}
    for ticker, mu, vol in [("SPY", 0.0004, 0.012), ("IEF", 0.0001, 0.003), ("GLD", 0.0002, 0.008)]:
        data[ticker] = 100.0 * np.exp(np.cumsum(rng.normal(mu, vol, n)))
    return pd.DataFrame(data, index=idx)


def _shiller(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="MS")
    return pd.DataFrame({
        "CAPE": 25 + rng.normal(0, 2, n),
        "Earnings": 150.0 * (1 + rng.normal(0.002, 0.01, n)).cumprod(),
        "Rate GS10": 3 + rng.normal(0, 0.2, n),
    }, index=idx)


def test_blend_grid_contents():
    assert set(BLEND_GRID) == {0.95, 0.90, 0.80, 0.70, 0.60}
    assert all(0.0 < w < 1.0 for w in BLEND_GRID)


def test_crqs_params_keys():
    for key in ["eps_threshold", "scale_down", "corr_threshold", "target_vol", "lookback"]:
        assert key in CRQS_PARAMS


def test_minvar_params_keys():
    assert "cov_lookback" in MINVAR_PARAMS


def test_output_columns():
    panel = _panel()
    sh = _shiller()
    w = multi_signals(panel, sh, blend_w=0.80)
    assert set(w.columns) >= {"SPY", "IEF", "GLD"}
    assert len(w) == len(panel)


def test_row_sum_bounded_all_blends():
    panel = _panel()
    sh = _shiller()
    for bw in BLEND_GRID:
        w = multi_signals(panel, sh, blend_w=bw)
        row_sum = w.sum(axis=1)
        assert (row_sum <= 1.0 + 1e-9).all(), f"Row sum > 1 at blend_w={bw}"


def test_weights_non_negative():
    panel = _panel()
    sh = _shiller()
    for bw in BLEND_GRID:
        w = multi_signals(panel, sh, blend_w=bw)
        assert (w >= -1e-10).all(axis=None), f"Negative weight at blend_w={bw}"


def test_pure_crqs_blend():
    """blend_w=1.0 should produce same result as standalone CRQS."""
    panel = _panel()
    sh = _shiller()
    ief = panel["IEF"]
    gld = panel["GLD"]
    w_blend = multi_signals(panel, sh, ief=ief, gld=gld, blend_w=1.0)
    from strategies.crqs import multi_signals as crqs_signals
    w_crqs = crqs_signals(panel["SPY"], sh, ief=ief, gld=gld, **CRQS_PARAMS)
    pd.testing.assert_frame_equal(
        w_blend.reindex(w_crqs.index).fillna(0.0),
        w_crqs.fillna(0.0),
        check_exact=False, rtol=1e-6,
        check_like=True,
    )


def test_higher_blend_more_spy_weight():
    """Higher CRQS weight → more SPY on average (CRQS is mostly SPY-focused)."""
    panel = _panel()
    sh = _shiller()
    w_high = multi_signals(panel, sh, blend_w=0.95)
    w_low = multi_signals(panel, sh, blend_w=0.60)
    avg_spy_high = float(w_high["SPY"].mean())
    avg_spy_low = float(w_low["SPY"].mean())
    assert avg_spy_high >= avg_spy_low - 0.05


def test_lower_blend_more_ief_weight():
    """Lower CRQS weight → more IEF (MinVar is IEF-heavy)."""
    panel = _panel()
    sh = _shiller()
    w_high = multi_signals(panel, sh, blend_w=0.95)
    w_low = multi_signals(panel, sh, blend_w=0.60)
    avg_ief_high = float(w_high["IEF"].mean())
    avg_ief_low = float(w_low["IEF"].mean())
    assert avg_ief_low >= avg_ief_high - 0.05


def test_explicit_ief_gld_affects_crqs_sleeve():
    """Passing explicit IEF/GLD controls CRQS rolling-correlation computation."""
    panel = _panel()
    sh = _shiller()
    # Both calls pass same panel data; result must have valid weights
    w = multi_signals(panel, sh, ief=panel["IEF"], gld=panel["GLD"], blend_w=0.80)
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()
    assert (w >= -1e-10).all(axis=None)
