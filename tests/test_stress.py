"""Tests for backtest/stress.py — SYNTHETIC DATA ONLY (Phase-2 discipline:
the harness must never touch champion returns before Phase 3)."""
import numpy as np
import pandas as pd
import pytest

from backtest.stress import (BEAR_WINDOWS, regime_replay, costed_returns,
                             perturbation_grid, collapse_verdict)


def _synth(start="1999-01-01", end="2023-12-31", mu=0.0003, sd=0.01, seed=7):
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sd, len(idx)), index=idx)


def test_regime_replay_covers_all_four_windows():
    r = _synth()
    out = regime_replay(r)
    assert set(out) == set(BEAR_WINDOWS)
    for name, row in out.items():
        assert row["strategy"]["n_days"] > 0, name


def test_regime_replay_no_data_reports_zero_days():
    r = _synth(start="2024-01-01", end="2024-06-30")
    out = regime_replay(r)
    assert all(row["strategy"]["n_days"] == 0 for row in out.values())


def test_regime_replay_drawdown_sign():
    idx = pd.bdate_range("2020-02-19", "2020-03-23")
    r = pd.Series(-0.02, index=idx)  # steady crash
    out = regime_replay(r)
    m = out["covid_2020"]["strategy"]
    assert m["max_drawdown"] < -0.3
    assert m["total_return"] < 0


def test_costed_returns_no_lookahead():
    """Exposure set on day t must earn day t+1's return, not day t's."""
    idx = pd.bdate_range("2022-01-03", periods=4)
    asset = pd.Series([0.0, 0.10, 0.0, 0.0], index=idx)
    expo = pd.Series([0.0, 0.0, 1.0, 1.0], index=idx)  # enters AFTER the +10% day
    r = costed_returns(expo, asset, cost_per_turnover=0.0)
    assert r.sum() == pytest.approx(0.0)  # missed the move: no lookahead


def test_costed_returns_doubling_costs_doubles_drag():
    idx = pd.bdate_range("2022-01-03", periods=50)
    asset = pd.Series(0.0, index=idx)
    rng = np.random.default_rng(1)
    expo = pd.Series(rng.integers(0, 2, len(idx)).astype(float), index=idx)
    d1 = costed_returns(expo, asset, cost_multiplier=1.0).sum()
    d2 = costed_returns(expo, asset, cost_multiplier=2.0).sum()
    assert d1 < 0
    assert d2 == pytest.approx(2 * d1)


def test_perturbation_grid_v2_shape():
    """v2 params: 1 base + 4 one-at-a-time + 4 corners = 9 (post-dedupe <= 9)."""
    grid = perturbation_grid({"target_vol": 0.18, "lookback": 20},
                             int_params={"lookback"})
    assert grid[0] == {"target_vol": 0.18, "lookback": 20}
    assert 5 <= len(grid) <= 9
    lbs = {g["lookback"] for g in grid}
    assert lbs == {15, 20, 25}
    tvs = {round(g["target_vol"], 4) for g in grid}
    assert tvs == {0.135, 0.18, 0.225}


def test_collapse_verdict_flags_drawdown_breach():
    base = {"ann_sharpe": 1.0, "max_drawdown": -0.10}
    ok = [{"ann_sharpe": 0.9, "max_drawdown": -0.15}]
    bad = [{"ann_sharpe": 0.9, "max_drawdown": -0.25}]
    assert not collapse_verdict(base, ok)["collapsed"]
    v = collapse_verdict(base, bad)
    assert v["collapsed"] and v["failures"][0][1] == "drawdown_breach"


def test_collapse_verdict_flags_sharpe_collapse():
    base = {"ann_sharpe": 1.0, "max_drawdown": -0.10}
    bad = [{"ann_sharpe": 0.4, "max_drawdown": -0.10}]
    v = collapse_verdict(base, bad)
    assert v["collapsed"] and v["failures"][0][1] == "sharpe_collapse"
