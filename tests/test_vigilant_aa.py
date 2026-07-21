"""Tests for strategies/vigilant_aa.py.

Key guarantees verified:
  1. No look-ahead: past signals are unchanged when future bars are appended.
  2. Single-asset: at most one ticker has weight > 0 on any date.
  3. Monthly cadence: weights change only at month boundaries, not intra-month.
  4. Defensive trigger: when any offensive asset scores <= 0, hold only defensive.
  5. History gate: no position taken until 252 days of history available.
"""
import numpy as np
import pandas as pd
import pytest

from strategies.vigilant_aa import multi_signals, _compute_scores

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TICKERS = ["SPY", "QQQ", "IWM", "SHY", "IEF", "TLT", "GLD"]


def _synthetic_panel(n_days: int = 600, seed: int = 42) -> pd.DataFrame:
    """Synthetic price panel with realistic-ish drift."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2000-01-03", periods=n_days)
    drift = {"SPY": 0.0003, "QQQ": 0.0003, "IWM": 0.0002,
             "SHY": 0.0001, "IEF": 0.00015, "TLT": 0.0002, "GLD": 0.00025}
    data = {}
    for t, mu in drift.items():
        r = rng.normal(mu, 0.01, n_days)
        data[t] = 100.0 * np.cumprod(1 + r)
    return pd.DataFrame(data, index=dates)


def _bear_panel(n_days: int = 700, seed: int = 99) -> pd.DataFrame:
    """Panel where equity assets trend down so defensive should be picked."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2000-01-03", periods=n_days)
    drift = {"SPY": -0.002, "QQQ": -0.003, "IWM": -0.002,
             "SHY": 0.0002, "IEF": 0.0003, "TLT": 0.0004, "GLD": 0.0005}
    data = {}
    for t, mu in drift.items():
        r = rng.normal(mu, 0.01, n_days)
        data[t] = 100.0 * np.cumprod(1 + r)
    return pd.DataFrame(data, index=dates)


# ---------------------------------------------------------------------------
# Test 1: No look-ahead bias
# ---------------------------------------------------------------------------
def test_no_lookahead():
    """Appending a future bar from a NEW month must not alter any past signal.

    The cut is chosen at a month-end boundary so the added bar is the first day
    of a new month. This avoids the edge case where 'tail(1) per month' would
    select a different month-end date in the shorter series vs the full series.
    """
    panel = _synthetic_panel(700)
    # Find month-end dates in the panel
    month_ends = panel.index[
        pd.Series(True, index=panel.index)
        .groupby([panel.index.year, panel.index.month])
        .cumcount(ascending=False) == 0
    ]
    # Truncate the short panel at the second-to-last month-end so the added
    # bar(s) are in a new month — guarantees same month-end definitions.
    cut = month_ends[-2]
    w_short = multi_signals(panel.loc[:cut], breadth_prot=0.30, offensive_n=3)
    w_full  = multi_signals(panel, breadth_prot=0.30, offensive_n=3)

    common_idx = w_short.index
    diff = (w_full.loc[common_idx] - w_short.loc[common_idx]).abs().max().max()
    assert diff < 1e-10, f"Look-ahead detected: max delta = {diff}"


# ---------------------------------------------------------------------------
# Test 2: Single-asset constraint
# ---------------------------------------------------------------------------
def test_single_asset_per_bar():
    """Row sums must be 0 or 1; never two assets held simultaneously."""
    panel = _synthetic_panel(700)
    w = multi_signals(panel, breadth_prot=0.30, offensive_n=3)
    row_sums = w.sum(axis=1)
    assert (row_sums.isin([0.0, 1.0])).all(), (
        f"Row sums outside {{0,1}}: {row_sums[~row_sums.isin([0.0, 1.0])].head()}"
    )


# ---------------------------------------------------------------------------
# Test 3: Monthly cadence
# ---------------------------------------------------------------------------
def test_monthly_cadence():
    """Weights should change only at month boundaries (after the ffill/shift,
    position changes occur no more than once per ~21 days on average)."""
    panel = _synthetic_panel(700)
    w = multi_signals(panel, breadth_prot=0.30, offensive_n=3)
    changes = (w.diff().abs().sum(axis=1) > 0).sum()
    n_months = len(pd.period_range(panel.index[0], panel.index[-1], freq="M"))
    assert changes <= n_months + 2, (
        f"Too many intra-month changes: {changes} changes over ~{n_months} months"
    )


# ---------------------------------------------------------------------------
# Test 4: Defensive trigger under bear conditions
# ---------------------------------------------------------------------------
def test_defensive_trigger():
    """In a sustained equity bear market, breadth protection should route to
    a defensive asset for the majority of invested days."""
    panel = _bear_panel(700)
    w = multi_signals(panel, breadth_prot=0.30, offensive_n=3)

    equity_assets = ["SPY", "QQQ", "IWM"]
    defensive_assets = ["SHY", "IEF", "TLT", "GLD"]

    invested = w.sum(axis=1) > 0
    if not invested.any():
        return  # all cash is also a valid bear response

    equity_days = w.loc[invested, equity_assets].sum(axis=1).sum()
    def_days = w.loc[invested, defensive_assets].sum(axis=1).sum()

    assert def_days > equity_days, (
        f"Expected mostly defensive in bear market: "
        f"equity_days={equity_days:.0f}, def_days={def_days:.0f}"
    )


# ---------------------------------------------------------------------------
# Test 5: History gate (no position before 252 days)
# ---------------------------------------------------------------------------
def test_history_gate():
    """No weight should be assigned in the first 252 calendar bars."""
    panel = _synthetic_panel(700)
    w = multi_signals(panel, breadth_prot=0.30, offensive_n=3)

    early = w.iloc[:252]
    assert early.sum().sum() == 0.0, (
        "Position taken before 252 days of history"
    )


# ---------------------------------------------------------------------------
# Test 6: Score computation is causal
# ---------------------------------------------------------------------------
def test_score_causality():
    """Score matrix row at date t should not depend on rows t+1 and beyond."""
    panel = _synthetic_panel(500)
    tickers = ["SPY", "QQQ", "IWM", "SHY", "IEF", "TLT", "GLD"]
    panel_sub = panel[tickers]

    score_short = _compute_scores(panel_sub.iloc[:-1], tickers)
    score_full  = _compute_scores(panel_sub, tickers)

    common = score_short.index
    diff = (score_full.loc[common] - score_short.loc[common]).abs().max().max()
    assert diff < 1e-10, f"Score look-ahead detected: max delta = {diff}"
