"""Tests for gtaa_full (E36) strategy — session 24."""
import numpy as np
import pandas as pd
import pytest

from strategies.gtaa_full import multi_signals, UNIVERSE, SLOT_WEIGHT


def _panel(n=600, seed=42):
    rng = np.random.default_rng(seed)
    data = {}
    for i, t in enumerate(UNIVERSE):
        px = 100.0 * (1 + rng.normal(0.0003, 0.01, n)).cumprod()
        data[t] = px
    idx = pd.date_range("2002-01-01", periods=n, freq="B")
    return pd.DataFrame(data, index=idx)


def test_output_shape():
    w = multi_signals(price_panel=_panel())
    assert set(w.columns) == set(UNIVERSE)
    assert len(w) == 600


def test_weights_non_negative():
    w = multi_signals(price_panel=_panel())
    assert (w >= -1e-9).all().all()


def test_row_sum_leq_one():
    w = multi_signals(price_panel=_panel())
    assert (w.sum(axis=1) <= 1.0 + 1e-9).all()


def test_max_weight_per_asset():
    w = multi_signals(price_panel=_panel())
    assert (w.max() <= SLOT_WEIGHT + 1e-9).all()


def test_band_zero_binary_weights():
    """band=0 should yield only 0 or SLOT_WEIGHT values (no hysteresis)."""
    w = multi_signals(price_panel=_panel(), band=0.0)
    unique_vals = set(np.round(w.values.ravel(), 6))
    assert unique_vals <= {0.0, round(SLOT_WEIGHT, 6)}


def test_no_lookahead():
    """Truncating the series at row 400 must not change rows up to 350."""
    panel = _panel(600)
    w1 = multi_signals(price_panel=panel.iloc[:400])
    w2 = multi_signals(price_panel=panel)
    pd.testing.assert_frame_equal(
        w1.iloc[:350],
        w2.iloc[:350],
        check_names=False,
        rtol=1e-6,
    )


def test_missing_ticker_gets_zero_weight():
    """A panel missing one ticker must give 0 weight for that column."""
    panel = _panel()
    panel_miss = panel.drop(columns=["EFA"])
    w = multi_signals(price_panel=panel_miss)
    assert "EFA" in w.columns
    assert (w["EFA"].abs() < 1e-9).all()


def test_sma_window_respected():
    """With a window larger than the series, all weights must be 0."""
    panel = _panel(50)
    w = multi_signals(price_panel=panel, sma_window=300)
    assert (w.abs() < 1e-9).all().all()
