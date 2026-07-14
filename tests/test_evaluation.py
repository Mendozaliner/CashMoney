"""Sanity tests for the statistical-honesty layer."""
import numpy as np
import pandas as pd

from backtest import evaluation as ev


def _series(mu, sigma, n=1500, seed=1):
    rng = np.random.default_rng(seed)
    return rng.normal(mu, sigma, n)


def test_sharpe_sign_and_scale():
    assert ev.sharpe_ratio(_series(0.0005, 0.01)) > 0
    assert ev.sharpe_ratio(_series(-0.0005, 0.01)) < 0


def test_deflated_sharpe_falls_with_more_trials():
    r = _series(0.0004, 0.01, seed=7)
    win = ev.sharpe_ratio(r)
    few = ev.deflated_sharpe_ratio(r, [win] + list(np.linspace(0.1, win, 4)))
    many = ev.deflated_sharpe_ratio(r, [win] + list(np.linspace(0.1, win, 200)))
    assert many < few, (few, many)      # more trials -> more deflation


def test_pure_noise_does_not_clear_the_gate():
    noise = _series(0.0, 0.01, seed=3)
    bench = _series(0.0, 0.01, seed=4)
    ci = ev.bootstrap_difference_ci(noise, bench, "sharpe", n=2000)
    assert not ci.clears_noise                       # zero-edge -> CI spans 0


def test_real_edge_clears_the_gate():
    strat = _series(0.0006, 0.008, n=3000, seed=11)
    bench = _series(0.0001, 0.008, n=3000, seed=12)
    ci = ev.bootstrap_difference_ci(strat, bench, "sharpe", n=2000)
    assert ci.clears_noise and ci.lo > 0


def test_identical_series_zero_difference():
    r = _series(0.0003, 0.01, seed=5)
    ci = ev.bootstrap_difference_ci(r, r, "sharpe", n=1000)
    assert abs(ci.point) < 1e-9 and not ci.clears_noise


def test_tax_reduces_terminal_value():
    # 20 short-term round trips, each +3%
    tr = [0.03] * 20
    hd = [30] * 20
    gross = np.prod([1 + x for x in tr])
    after = ev.after_tax_from_trades(tr, hd, st_rate=0.35, lt_rate=0.15)
    assert after < gross
    # long-term holding is taxed more lightly than the same gains short-term
    st = ev.after_tax_from_trades([0.8], [30])
    lt = ev.after_tax_from_trades([0.8], [500])
    assert lt > st


def test_do_nothing_can_win():
    # churny strategy, modest edge, all short-term; index compounds untaxed
    tr = [0.01] * 50
    hd = [20] * 50
    idx = _series(0.0005, 0.01, n=2000, seed=9)
    v = ev.do_nothing_verdict(tr, hd, idx)
    assert isinstance(v.strategy_wins, bool) and "buy-and-hold" in str(v)


def test_probabilistic_sharpe_bounds():
    p = ev.probabilistic_sharpe_ratio(_series(0.0004, 0.01))
    assert 0.0 <= p <= 1.0
