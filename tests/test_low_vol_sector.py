"""Tests for strategies/low_vol_sector.py."""
import sys
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import pytest

from strategies import low_vol_sector as lvs
from data import loader


@pytest.fixture(scope="module")
def sector_panel():
    return loader.load_universe(lvs.SECTOR_ETFS, start="2005-01-01", end="2023-12-31")


def test_weight_sum_le_one(sector_panel):
    """Row sums of weights must not exceed 1.0 (no leverage)."""
    w = lvs.multi_signals(sector_panel, top_n=4)
    assert (w.sum(axis=1) > 1.0 + 1e-9).sum() == 0, "Row sum > 1.0 found"


def test_weight_non_negative(sector_panel):
    """All weights >= 0 (long-only per G1)."""
    w = lvs.multi_signals(sector_panel, top_n=4)
    assert (w < -1e-9).sum().sum() == 0


def test_columns_in_whitelist(sector_panel):
    """Strategy only holds whitelisted sector ETFs."""
    w = lvs.multi_signals(sector_panel, top_n=4)
    for col in w.columns:
        assert col in lvs.SECTOR_ETFS, f"{col} not in SECTOR_ETFS"


def test_no_lookahead(sector_panel):
    """Removing the last month does not change earlier signals (no lookahead)."""
    cut = sector_panel.iloc[:-23]
    w_full = lvs.multi_signals(sector_panel, top_n=3)
    w_cut = lvs.multi_signals(cut, top_n=3)
    common = w_full.index.intersection(w_cut.index)
    diff = (w_full.loc[common] - w_cut.loc[common]).abs().max().max()
    assert diff < 1e-9, f"Lookahead detected: max delta = {diff}"


def test_monthly_rebalance(sector_panel):
    """Weights rebalance roughly monthly, not daily.

    Due to pandas resample('ME') producing calendar month-end dates that may
    not be trading days, each calendar month can see 1-2 weight transitions
    (prior-month weight lands on first trading day; current-month weight lands
    on last trading day if it is a trading day). The invariant is that rebalances
    happen << once per day — the rebalance count per year should be << 24 (2x monthly)
    but >> 240 (daily).
    """
    w = lvs.multi_signals(sector_panel, top_n=4)
    changes = w.diff().abs().sum(axis=1)
    n_changes = int((changes > 1e-9).sum())
    n_years = (sector_panel.index[-1] - sector_panel.index[0]).days / 365.25
    changes_per_year = n_changes / n_years
    # Monthly rebalance => 12-24 changes/year (allow 2 per month);
    # daily rebalance would be ~252/year
    assert changes_per_year <= 28, f"Too frequent: {changes_per_year:.1f} changes/year (max 28)"
    assert changes_per_year >= 8, f"Too infrequent: {changes_per_year:.1f} changes/year (min 8)"
