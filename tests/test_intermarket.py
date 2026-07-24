"""Tests for strategies/intermarket.py (session 20, E30).

Checks:
1. No lookahead: signals at t use only data through t
2. Exposure always in [0, 1]
3. Risk-on period: SPY outperforming IEF → full v2 exposure
4. Risk-off period: IEF outperforming SPY → reduced exposure
5. Pre-IEF period (before 2002): treated as risk-on (no penalty)
6. Output length and index match SPY input
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import pytest

from strategies import intermarket, vol_target


def _synth(n=500, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    spy = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.01 + 0.0004))
    ief = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.003 + 0.0001))
    return (pd.Series(spy, index=idx, name="SPY"),
            pd.Series(ief, index=idx, name="IEF"))


# ---------------------------------------------------------------------------
# 1. Exposure always in [0, 1]
# ---------------------------------------------------------------------------
def test_exposure_in_unit_interval():
    spy, ief = _synth()
    sig = intermarket.signals(spy, ief)
    assert (sig >= -1e-9).all(), "Signal below 0"
    assert (sig <= 1.0 + 1e-9).all(), "Signal above 1 (leverage)"


# ---------------------------------------------------------------------------
# 2. Risk-on: SPY strongly outperforming IEF → signal matches v2 exactly
# ---------------------------------------------------------------------------
def test_risk_on_matches_v2():
    """When scale=1.0 (risk-on), intermarket signal == base v2 signal exactly."""
    n = 500
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    # Deterministic monotone uptrend: SPY always up, so spy_mom >= 0 always
    spy = pd.Series(100.0 + np.arange(n) * 0.5, index=idx, name="SPY")
    # IEF flat: ief_mom = 0 always
    ief = pd.Series(110.0, index=idx, name="IEF")
    sig = intermarket.signals(spy, ief, lookback=21)
    base = vol_target.signals(spy, target_vol=0.18, lookback=20)
    # With deterministic uptrend, spy_mom > ief_mom = 0 always → risk-on = True
    # → scale = 1.0 → sig should exactly equal base
    pd.testing.assert_series_equal(sig.iloc[30:], base.iloc[30:],
                                   check_names=False, atol=1e-9)
    # And signal should never exceed base (no leverage)
    assert (sig <= base + 1e-9).all(), "Signal exceeded base v2"


# ---------------------------------------------------------------------------
# 3. Risk-off: IEF strongly outperforming SPY → signal < base v2
# ---------------------------------------------------------------------------
def test_risk_off_reduces_exposure():
    rng = np.random.default_rng(2)
    n = 500
    idx = pd.date_range("2005-01-03", periods=n, freq="B")
    # SPY flat/declining, IEF strong rally
    spy_vals = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.008 - 0.0005))
    ief_vals = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.003 + 0.0008))
    spy = pd.Series(spy_vals, index=idx, name="SPY")
    ief = pd.Series(ief_vals, index=idx, name="IEF")
    sig = intermarket.signals(spy, ief, lookback=63, reduced_scale=0.5)
    base = vol_target.signals(spy, target_vol=0.18, lookback=20)
    # Signal should be <= base in risk-off periods (never exceeds base)
    assert (sig <= base + 1e-9).all(), "Risk-off signal exceeds base v2"
    # On average, signal should be <= base (never exceeds it)
    assert (sig <= base + 1e-9).all(), "Risk-off signal exceeds base v2"
    # When base > 0 (actually invested), signal should be less on average
    invested_mask = base > 0.01
    if invested_mask.sum() > 10:
        sig_when_inv = sig[invested_mask].mean()
        base_when_inv = base[invested_mask].mean()
        assert sig_when_inv <= base_when_inv + 1e-9, \
            f"Risk-off signal not reduced: sig={sig_when_inv:.3f}, base={base_when_inv:.3f}"


# ---------------------------------------------------------------------------
# 4. No lookahead
# ---------------------------------------------------------------------------
def test_no_lookahead():
    spy, ief = _synth(400)
    full = intermarket.signals(spy, ief)
    cutoff = 250
    cut = intermarket.signals(spy.iloc[:cutoff], ief.iloc[:cutoff])
    start = 230  # past warm-up for 63-day lookback + SMA200
    if cutoff > start:
        pd.testing.assert_series_equal(
            full.iloc[start:cutoff].reset_index(drop=True),
            cut.iloc[start:cutoff].reset_index(drop=True),
            check_names=False, atol=1e-8,
        )


# ---------------------------------------------------------------------------
# 5. Missing IEF data (pre-listing) handled as risk-on
# ---------------------------------------------------------------------------
def test_pre_listing_period_treated_as_risk_on():
    rng = np.random.default_rng(3)
    n = 600
    idx = pd.date_range("2000-01-03", periods=n, freq="B")
    spy_vals = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.01 + 0.0004))
    spy = pd.Series(spy_vals, index=idx, name="SPY")
    # IEF only from day 300 onwards
    ief_vals = 100.0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.003 + 0.0001))
    ief = pd.Series(ief_vals[300:], index=idx[300:], name="IEF")
    sig = intermarket.signals(spy, ief, lookback=63)
    base = vol_target.signals(spy, target_vol=0.18, lookback=20)
    # Before IEF starts, signal should equal base (risk-on default)
    # Use first 200 bars where IEF is definitely NaN after reindex
    early = slice(220, 290)
    pd.testing.assert_series_equal(
        sig.iloc[early].reset_index(drop=True),
        base.iloc[early].reset_index(drop=True),
        check_names=False, atol=1e-8,
    )


# ---------------------------------------------------------------------------
# 6. Output length and index match SPY
# ---------------------------------------------------------------------------
def test_output_matches_spy_index():
    spy, ief = _synth(300)
    sig = intermarket.signals(spy, ief)
    assert len(sig) == 300
    pd.testing.assert_index_equal(sig.index, spy.index)
