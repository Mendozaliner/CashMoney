"""Phase-3 stress-test harness (built s17, 2026-07-22 — ENGINEERING ONLY).

Implements the three Phase-3 charter tests as reusable, strategy-agnostic
tools so that when the desk reaches Phase 3 the graduation candidate can be
stress-tested in one session without ad-hoc code:

1. BEAR-REGIME REPLAY — evaluate a daily-return series inside the four
   charter bear windows (dot-com 2000-02, GFC 2007-09, COVID 2020, 2022).
2. DOUBLED COSTS — rerun an exposure-based strategy with a cost multiplier
   (charter: 2x the standard 0.1% commission + 0.05% slippage).
3. PARAMETER PERTURBATION — generate a +/-25% one-at-a-time perturbation set
   for a parameter dict, plus the four corner combinations for 2-parameter
   strategies (v2 has exactly 2 tunables: target_vol, lookback).

Sources: Lopez de Prado (2018) "Advances in Financial Machine Learning" ch.14
(strategy risk / stress paths); Bailey et al. (2014) deflated Sharpe; charter
Phase-3 spec. IMPORTANT: this module is tested on SYNTHETIC data only until a
Phase-3 graduation candidate exists — running it on the champion during Phase 2
would leak holdout/tuning information. Do NOT invoke on real champion returns
before Phase 3 is declared.
"""
from __future__ import annotations
import itertools
import numpy as np
import pandas as pd

# Charter bear regimes (peak -> trough, closed intervals, calendar dates)
BEAR_WINDOWS = {
    "dotcom_2000_02": ("2000-03-24", "2002-10-09"),
    "gfc_2007_09": ("2007-10-09", "2009-03-09"),
    "covid_2020": ("2020-02-19", "2020-03-23"),
    "bear_2022": ("2022-01-03", "2022-10-12"),
}

TRADING_DAYS = 252


def _metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) == 0:
        return {"n_days": 0, "total_return": np.nan, "ann_sharpe": np.nan,
                "max_drawdown": np.nan}
    curve = (1 + r).cumprod()
    dd = (curve / curve.cummax() - 1).min()
    mu, sd = r.mean(), r.std()
    sharpe = np.sqrt(TRADING_DAYS) * mu / sd if sd > 0 else np.nan
    return {"n_days": int(len(r)),
            "total_return": float(curve.iloc[-1] - 1),
            "ann_sharpe": float(sharpe),
            "max_drawdown": float(dd)}


def regime_replay(returns: pd.Series, benchmark: pd.Series | None = None,
                  windows: dict | None = None) -> dict:
    """Metrics for a daily-return series inside each bear window.

    Returns {regime: {strategy: metrics, benchmark: metrics|None}}.
    Regimes with no overlapping data report n_days=0 (caller must not treat
    absence of data as passing).
    """
    windows = windows or BEAR_WINDOWS
    out = {}
    for name, (start, end) in windows.items():
        seg = returns.loc[start:end]
        row = {"strategy": _metrics(seg)}
        row["benchmark"] = _metrics(benchmark.loc[start:end]) if benchmark is not None else None
        out[name] = row
    return out


def costed_returns(exposure: pd.Series, asset_returns: pd.Series,
                   cash_yield_daily: pd.Series | float = 0.0,
                   cost_per_turnover: float = 0.0015,
                   cost_multiplier: float = 1.0) -> pd.Series:
    """Strategy daily returns from an exposure path with explicit costs.

    exposure is applied to the NEXT day's asset return (no lookahead).
    cost_per_turnover: charter standard 0.0015 (0.1% commission + 0.05%
    slippage); Phase 3 doubles it via cost_multiplier=2.0.
    """
    exp = exposure.shift(1).fillna(0.0)
    turnover = exposure.diff().abs().fillna(exposure.abs())
    if isinstance(cash_yield_daily, (int, float)):
        cash = float(cash_yield_daily)
        cash_leg = (1 - exp) * cash
    else:
        cash_leg = (1 - exp) * cash_yield_daily.shift(1).fillna(0.0)
    gross = exp * asset_returns + cash_leg
    return gross - turnover.shift(0) * cost_per_turnover * cost_multiplier


def perturbation_grid(params: dict, pct: float = 0.25,
                      int_params: set | None = None) -> list[dict]:
    """+/-pct one-at-a-time perturbations + corners (if exactly 2 params).

    Returns list of param dicts, base config first. For int_params the
    perturbed value is rounded to int (e.g. lookback windows).
    """
    int_params = int_params or set()
    keys = list(params)

    def cast(k, v):
        return int(round(v)) if k in int_params else v

    grid = [dict(params)]
    for k in keys:
        for sign in (+1, -1):
            p = dict(params)
            p[k] = cast(k, params[k] * (1 + sign * pct))
            grid.append(p)
    if len(keys) == 2:
        for s1, s2 in itertools.product((+1, -1), repeat=2):
            p = {keys[0]: cast(keys[0], params[keys[0]] * (1 + s1 * pct)),
                 keys[1]: cast(keys[1], params[keys[1]] * (1 + s2 * pct))}
            grid.append(p)
    # dedupe (rounding can collide)
    seen, uniq = set(), []
    for p in grid:
        t = tuple(sorted(p.items()))
        if t not in seen:
            seen.add(t)
            uniq.append(p)
    return uniq


def collapse_verdict(base: dict, stressed: list[dict],
                     sharpe_floor_frac: float = 0.5,
                     dd_limit: float = -0.20) -> dict:
    """Charter collapse test: does performance collapse under stress?

    base / stressed: metric dicts with ann_sharpe and max_drawdown.
    COLLAPSE if any stressed run has Sharpe < sharpe_floor_frac * base Sharpe
    (when base Sharpe > 0) or max_drawdown worse than dd_limit.
    """
    failures = []
    for i, m in enumerate(stressed):
        if base.get("ann_sharpe", 0) > 0 and m.get("ann_sharpe", np.nan) < sharpe_floor_frac * base["ann_sharpe"]:
            failures.append((i, "sharpe_collapse", m.get("ann_sharpe")))
        if m.get("max_drawdown", 0) < dd_limit:
            failures.append((i, "drawdown_breach", m.get("max_drawdown")))
    return {"collapsed": bool(failures), "n_stressed": len(stressed),
            "failures": failures}
