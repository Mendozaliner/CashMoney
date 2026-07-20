"""Tests for strategies/market_breadth.py."""
import sys
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import pytest

from strategies import market_breadth as mb
from data import loader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def spy_data():
    return loader.load_ohlcv("SPY", start="2010-01-01", end="2023-12-31")["Close"]


@pytest.fixture(scope="module")
def sector_panel():
    tickers = mb.SECTOR_ETFS
    return loader.load_universe(tickers, start="2010-01-01", end="2023-12-31")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_breadth_score_bounds(spy_data, sector_panel):
    """Breadth score is always in [0, 1]."""
    bd = mb.breadth_score(sector_panel)
    assert bd.min() >= 0.0 - 1e-9
    assert bd.max() <= 1.0 + 1e-9


def test_breadth_score_nan_handled(spy_data, sector_panel):
    """No NaN in breadth score after warmup."""
    bd = mb.breadth_score(sector_panel, sma_window=200)
    assert bd.iloc[300:].isna().sum() == 0


def test_signal_bounds(spy_data, sector_panel):
    """Breadth signal is in [0, 1] at all times."""
    sig = mb.signals(spy_data, sector_panel.reindex(spy_data.index))
    assert sig.min() >= 0.0 - 1e-9
    assert sig.max() <= 1.0 + 1e-9


def test_no_lookahead(spy_data, sector_panel):
    """Removing the final bar cannot change any prior signal — no lookahead."""
    sec = sector_panel.reindex(spy_data.index)
    sig_full = mb.signals(spy_data, sec)
    sig_minus1 = mb.signals(spy_data.iloc[:-1], sec.iloc[:-1])
    common = sig_full.index.intersection(sig_minus1.index)
    diff = (sig_full.loc[common] - sig_minus1.loc[common]).abs().max()
    assert diff < 1e-9, f"Lookahead detected: max delta = {diff}"


def test_gate_hysteresis(spy_data, sector_panel):
    """Hysteresis (0.7/0.5 band) produces fewer gate transitions than tight (0.6/0.6)."""
    sec = sector_panel.reindex(spy_data.index)
    sig_hysteresis = mb.signals(spy_data, sec, upper_band=0.7, lower_band=0.5)
    sig_tight = mb.signals(spy_data, sec, upper_band=0.6, lower_band=0.6)
    # Gate transitions: days where binary gate flips (change > 0.5)
    def n_transitions(sig):
        return int((sig.shift(1).fillna(sig.iloc[0]) - sig).abs().gt(0.5).sum())
    h_trans = n_transitions(sig_hysteresis)
    t_trans = n_transitions(sig_tight)
    assert h_trans <= t_trans, (
        f"Hysteresis ({h_trans}) should not produce MORE transitions than tight ({t_trans})"
    )
