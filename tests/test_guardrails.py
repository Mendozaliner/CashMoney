"""Tests for backtest/guardrails.py (s10). Reporting-only ops guardrails."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from backtest import guardrails as g


def test_exposure_ok():
    assert g.check_exposure(1.0)["ok"]
    assert g.check_exposure(0.0)["ok"]

def test_exposure_leverage_fails():
    assert not g.check_exposure(1.3)["ok"]

def test_exposure_short_fails():
    assert not g.check_exposure(-0.2)["ok"]

def test_instruments_whitelist():
    assert g.check_instruments(["SPY", "GLD"])["ok"]
    assert not g.check_instruments(["SPY", "SPXW_PUT"])["ok"]

def test_concentration_single_stock():
    assert not g.check_concentration({"NVDA": 0.35, "SPY": 0.65})["ok"]
    assert g.check_concentration({"NVDA": 0.15, "SPY": 0.85})["ok"]

def test_concentration_sector_and_index_exempt():
    assert not g.check_concentration({"XLK": 0.40, "SPY": 0.60})["ok"]
    assert g.check_concentration({"SPY": 1.0})["ok"]  # broad index exempt

def test_concentration_short_flagged():
    assert not g.check_concentration({"SPY": -0.5})["ok"]

def test_drawdown_ladder():
    assert g.drawdown_level(100, 100)["level"] == "GREEN"
    assert g.drawdown_level(89, 100)["level"].startswith("AMBER")
    assert g.drawdown_level(84, 100)["level"].startswith("RED")
    assert g.drawdown_level(79, 100)["level"].startswith("BREACH")

def test_staleness():
    assert g.staleness_guard(0)["ok"]
    assert not g.staleness_guard(6)["ok"]

def test_vol_spike_quiet_and_spike():
    rng = np.random.default_rng(7)
    quiet = pd.Series(rng.normal(0, 0.005, 400))
    assert g.vol_spike_flag(quiet)["ok"]
    spiky = pd.Series(np.concatenate([rng.normal(0, 0.004, 380),
                                      rng.normal(0, 0.03, 20)]))
    assert not g.vol_spike_flag(spiky)["ok"]

def test_run_all_current_portfolio_green():
    port = {"positions": {"SPY": {"units": 1.333476, "last_px": 754.81}},
            "cash": 0.0,
            "last_mark": {"value": 1006.52},
            "history": [{"value": 999.0}, {"value": 1006.52}]}
    rep = g.run_all(port, stale_days=0)
    assert rep["all_ok"], rep
    assert abs(rep["nav"] - 1006.52) < 0.05

def test_run_all_flags_leverage():
    # Leverage in this book appears as negative cash (borrowed to buy).
    port = {"positions": {"SPY": {"units": 2.0, "last_px": 754.81}},
            "cash": -700.0, "last_mark": {"value": 809.62}, "history": []}
    rep = g.run_all(port, stale_days=0)
    assert not rep["all_ok"]
