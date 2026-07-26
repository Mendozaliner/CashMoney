"""Tests for session 22 new strategies: cape_tilt, yield_curve, tactical_bond.

Each strategy is tested on synthetic data for:
1. Output shape and index match input
2. Exposure in [0, 1] (or weight sums ≤ 1.0 for multi-asset)
3. No lookahead (truncating future doesn't change past signals)
4. Core mechanics (tilt reduces signal, inverted curve reduces signal, etc.)
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import pytest

from strategies import vol_target, cape_tilt, yield_curve, tactical_bond


# ---------------------------------------------------------------------------
# Shared synthetic price generators
# ---------------------------------------------------------------------------
def _spy(n=600, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    vals = 200.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.01 + 0.0004))
    return pd.Series(vals, index=idx, name="SPY")


def _ief(n=600, seed=2):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    vals = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.003 + 0.0001))
    return pd.Series(vals, index=idx, name="IEF")


def _shy(n=600, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    vals = 85.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.001 + 0.00005))
    return pd.Series(vals, index=idx, name="SHY")


def _cape_monthly(n_months=240, seed=4):
    """Synthetic monthly CAPE series (values 15-45)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2005-01-01", periods=n_months, freq="MS")
    vals = 25.0 + np.cumsum(rng.standard_normal(n_months) * 0.3)
    vals = np.clip(vals, 10, 60)
    return pd.Series(vals, index=idx, name="CAPE")


# ---------------------------------------------------------------------------
# cape_tilt.py tests
# ---------------------------------------------------------------------------
class TestCapeTilt:
    """Tests for cape_tilt.signals() using monkey-patching of load_shiller."""

    def _patch_shiller(self, cape_series, monkeypatch):
        """Replace load_shiller with a function returning a minimal DataFrame."""
        import strategies.cape_tilt as ct_mod
        import data.loader as loader_mod

        df = pd.DataFrame({"CAPE": cape_series})

        def fake_load_shiller(start=None, end=None):
            return df

        monkeypatch.setattr(loader_mod, "load_shiller", fake_load_shiller)

    def test_output_matches_spy_index(self, monkeypatch):
        spy = _spy()
        cape = _cape_monthly()
        self._patch_shiller(cape, monkeypatch)
        sig = cape_tilt.signals(spy, cape_pct=0.90, tilt=0.25)
        assert len(sig) == len(spy), "Output length mismatch"
        pd.testing.assert_index_equal(sig.index, spy.index)

    def test_exposure_in_unit_interval(self, monkeypatch):
        spy = _spy()
        cape = _cape_monthly()
        self._patch_shiller(cape, monkeypatch)
        for pct, tilt in [(0.90, 0.15), (0.90, 0.35), (0.85, 0.25)]:
            sig = cape_tilt.signals(spy, cape_pct=pct, tilt=tilt)
            assert (sig >= -1e-9).all(), f"Below 0 for pct={pct},tilt={tilt}"
            assert (sig <= 1.0 + 1e-9).all(), f"Above 1 for pct={pct},tilt={tilt}"

    def test_tilt_never_exceeds_base(self, monkeypatch):
        """CAPE tilt can only REDUCE exposure, never increase it."""
        spy = _spy()
        cape = _cape_monthly()
        self._patch_shiller(cape, monkeypatch)
        sig = cape_tilt.signals(spy, cape_pct=0.80, tilt=0.25)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        assert (sig <= base + 1e-9).all(), "CAPE tilt exceeded base v2 signal"

    def test_no_lookahead(self, monkeypatch):
        spy = _spy(700)
        cape = _cape_monthly(280)
        self._patch_shiller(cape, monkeypatch)
        full = cape_tilt.signals(spy, cape_pct=0.90, tilt=0.25)
        cutoff = 450
        cut = cape_tilt.signals(spy.iloc[:cutoff], cape_pct=0.90, tilt=0.25)
        start = 220  # past warm-up for SMA200 + CAPE expanding window
        pd.testing.assert_series_equal(
            full.iloc[start:cutoff].reset_index(drop=True),
            cut.iloc[start:cutoff].reset_index(drop=True),
            check_names=False, atol=1e-9,
        )

    def test_zero_tilt_equals_v2(self, monkeypatch):
        """With tilt=0, CAPE tilt should reproduce v2 exactly."""
        spy = _spy()
        cape = _cape_monthly()
        self._patch_shiller(cape, monkeypatch)
        sig = cape_tilt.signals(spy, cape_pct=0.90, tilt=0.00)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        pd.testing.assert_series_equal(sig, base, check_names=False, atol=1e-9)


# ---------------------------------------------------------------------------
# yield_curve.py tests
# ---------------------------------------------------------------------------
class TestYieldCurve:

    def test_output_matches_spy_index(self):
        spy, ief, shy = _spy(), _ief(), _shy()
        sig = yield_curve.signals(spy, ief=ief, shy=shy, lookback=63)
        assert len(sig) == len(spy)
        pd.testing.assert_index_equal(sig.index, spy.index)

    def test_exposure_in_unit_interval(self):
        spy, ief, shy = _spy(), _ief(), _shy()
        for lb, sc in [(63, 0.50), (126, 0.75), (252, 0.50)]:
            sig = yield_curve.signals(spy, ief=ief, shy=shy,
                                      lookback=lb, invert_scale=sc)
            assert (sig >= -1e-9).all(), f"Below 0 for lb={lb},sc={sc}"
            assert (sig <= 1.0 + 1e-9).all(), f"Above 1 for lb={lb},sc={sc}"

    def test_signal_never_exceeds_base(self):
        spy, ief, shy = _spy(), _ief(), _shy()
        sig = yield_curve.signals(spy, ief=ief, shy=shy, lookback=63,
                                  invert_scale=0.50)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        assert (sig <= base + 1e-9).all(), "Yield curve signal exceeded base"

    def test_scale_one_equals_v2(self):
        """With invert_scale=1.0, yield curve overlay should reproduce v2."""
        spy, ief, shy = _spy(), _ief(), _shy()
        sig = yield_curve.signals(spy, ief=ief, shy=shy, lookback=63,
                                  invert_scale=1.0)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        pd.testing.assert_series_equal(sig, base, check_names=False, atol=1e-9)

    def test_inverted_curve_reduces_exposure(self):
        """When short end strongly outperforms long end, signal < base v2."""
        n = 600
        idx = pd.date_range("2005-01-03", periods=n, freq="B")
        spy_vals = 200.0 * np.exp(np.cumsum(np.full(n, 0.0004)))
        spy = pd.Series(spy_vals, index=idx)
        # IEF flat, SHY strongly rising → inverted curve
        ief = pd.Series(100.0, index=idx, name="IEF")
        shy = pd.Series(85.0 * np.exp(np.arange(n) * 0.002), index=idx, name="SHY")
        sig = yield_curve.signals(spy, ief=ief, shy=shy, lookback=63,
                                  invert_scale=0.5)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        # After warm-up, signal should be reduced
        post_warmup = sig.iloc[200:]
        base_post = base.iloc[200:]
        if (base_post > 0.01).any():
            assert post_warmup[base_post > 0.01].mean() < base_post[base_post > 0.01].mean(), \
                "Expected inverted curve to reduce exposure"

    def test_no_lookahead(self):
        spy, ief, shy = _spy(700), _ief(700), _shy(700)
        full = yield_curve.signals(spy, ief=ief, shy=shy, lookback=63)
        cutoff = 450
        cut = yield_curve.signals(spy.iloc[:cutoff], ief=ief.iloc[:cutoff],
                                  shy=shy.iloc[:cutoff], lookback=63)
        start = 220
        pd.testing.assert_series_equal(
            full.iloc[start:cutoff].reset_index(drop=True),
            cut.iloc[start:cutoff].reset_index(drop=True),
            check_names=False, atol=1e-9,
        )


# ---------------------------------------------------------------------------
# tactical_bond.py tests
# ---------------------------------------------------------------------------
class TestTacticalBond:

    def test_output_is_dataframe_with_spy_ief_columns(self):
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief)
        assert isinstance(wts, pd.DataFrame)
        assert "SPY" in wts.columns, "Missing SPY column"
        assert "IEF" in wts.columns, "Missing IEF column"
        assert len(wts) == len(spy)

    def test_spy_weight_equals_v2(self):
        """SPY weight must exactly match v2 signal — equity sleeve unchanged."""
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief, ief_window=200)
        base = vol_target.signals(spy, target_vol=0.18, lookback=20)
        pd.testing.assert_series_equal(wts["SPY"], base, check_names=False, atol=1e-9)

    def test_weights_sum_leq_one(self):
        """Row sums must never exceed 1.0 (no leverage)."""
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief)
        row_sums = wts.sum(axis=1)
        assert (row_sums <= 1.0 + 1e-9).all(), "Weights summed > 1.0 (leverage!)"

    def test_weights_non_negative(self):
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief)
        assert (wts >= -1e-9).all().all(), "Negative weight found"

    def test_ief_weight_only_when_spy_in_cash(self):
        """IEF weight must be zero wherever v2 (SPY weight) is 1.0."""
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief)
        # Where SPY weight is exactly 1.0, IEF weight should be 0
        fully_invested = (wts["SPY"] >= 1.0 - 1e-9)
        if fully_invested.any():
            ief_when_invested = wts.loc[fully_invested, "IEF"]
            assert (ief_when_invested <= 1e-9).all(), \
                "IEF weight non-zero when SPY is at max weight"

    def test_frac_zero_means_no_ief(self):
        """With cash_ief_frac=0.0, IEF weight is always zero."""
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief, cash_ief_frac=0.0)
        assert (wts["IEF"].abs() <= 1e-9).all(), "IEF weight non-zero with frac=0"

    def test_index_matches_spy(self):
        spy, ief = _spy(), _ief()
        wts = tactical_bond.multi_signals(spy, ief=ief)
        pd.testing.assert_index_equal(wts.index, spy.index)
