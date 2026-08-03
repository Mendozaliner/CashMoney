"""Advanced risk metrics (session 28, S28).

Implements portfolio risk measures beyond Sharpe ratio:

    CVaR (Conditional Value at Risk)
        aka Expected Shortfall — average loss in the worst alpha% of days.
        Artzner, Delbaen, Eber & Heath (1999).

    Omega ratio
        Probability-weighted ratio of gains above threshold to losses below.
        Shadwick & Keating (2002).

    Calmar ratio
        Annualised return divided by maximum drawdown.
        Young (1991).

    Information ratio
        Excess return over benchmark divided by tracking error.
        Grinold & Kahn (1999).

    Tail ratio
        95th percentile daily return / abs(5th percentile daily return).
        Ratio > 1 means right-tail larger than left-tail.

    comprehensive_risk_report()
        Returns all metrics in a single dict for reporting.

References
----------
Artzner, P. et al. (1999). "Coherent Measures of Risk". Mathematical
    Finance 9(3): 203–228.
Shadwick, W.F. & Keating, C. (2002). "A Universal Performance Measure".
    Journal of Performance Measurement 6(3): 59–84.
Young, T.W. (1991). "Calmar Ratio: A Smoother Tool". Futures 20(1).
Grinold, R. & Kahn, R. (1999). "Active Portfolio Management". McGraw-Hill.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS = 252


# ── CVaR ─────────────────────────────────────────────────────────────────

def cvar(returns: np.ndarray | pd.Series,
         alpha: float = 0.05) -> float:
    """Conditional Value at Risk (Expected Shortfall).

    Average return in the worst `alpha` fraction of days.
    Returned as a positive number (magnitude of expected loss).

    Args:
        returns : Daily return series (not annualised).
        alpha   : Tail probability (0.05 → worst 5% of days).

    Returns:
        CVaR ≥ 0. A CVaR of 0.02 means the average loss in the worst
        5% of days is 2% per day.
    """
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    var_cutoff = np.quantile(r, alpha)
    tail = r[r <= var_cutoff]
    return float(-tail.mean()) if len(tail) > 0 else 0.0


def cvar_annualised(returns: np.ndarray | pd.Series,
                    alpha: float = 0.05) -> float:
    """CVaR scaled to annual (× √252)."""
    return cvar(returns, alpha) * np.sqrt(TRADING_DAYS)


# ── Omega ratio ───────────────────────────────────────────────────────────

def omega_ratio(returns: np.ndarray | pd.Series,
                threshold: float = 0.0) -> float:
    """Omega ratio: probability-weighted upside / downside.

    Omega = E[max(R − L, 0)] / E[max(L − R, 0)]
    where L is the threshold return (default 0).

    A ratio > 1 means more probability mass above the threshold than
    below. For most long-only strategies vs threshold=0, Omega > 1.

    Args:
        returns   : Daily return series.
        threshold : Minimum acceptable return (default 0 per day).

    Returns:
        Omega ratio ≥ 0. Returns inf if there are no losses.
    """
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    gains = np.sum(np.maximum(r - threshold, 0))
    losses = np.sum(np.maximum(threshold - r, 0))
    return float(gains / losses) if losses > 0 else float("inf")


# ── Calmar ratio ──────────────────────────────────────────────────────────

def calmar_ratio(returns: np.ndarray | pd.Series) -> float:
    """Calmar ratio: annualised return / maximum drawdown.

    Higher is better. A Calmar of 0.5 means you earn 50 cents of annual
    return for each dollar of maximum historical drawdown.

    Args:
        returns : Daily return series.

    Returns:
        Calmar ratio. Returns 0.0 if MaxDD is zero.
    """
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    cagr = float((1 + r).prod() ** (TRADING_DAYS / len(r)) - 1)
    cum = np.cumprod(1 + r)
    running_max = np.maximum.accumulate(cum)
    dd = (cum - running_max) / running_max
    max_dd = float(-dd.min())
    return cagr / max_dd if max_dd > 0 else 0.0


# ── Information ratio ─────────────────────────────────────────────────────

def information_ratio(strategy_returns: np.ndarray | pd.Series,
                      benchmark_returns: np.ndarray | pd.Series) -> float:
    """Annualised information ratio vs benchmark.

    IR = annualised(active_return) / annualised(tracking_error)
    where active_return = strategy − benchmark.

    Args:
        strategy_returns  : Daily strategy return series.
        benchmark_returns : Daily benchmark return series (same length).

    Returns:
        Information ratio (annualised). 0.5 is considered good.
    """
    s = np.asarray(strategy_returns)
    b = np.asarray(benchmark_returns)
    # Align lengths
    n = min(len(s), len(b))
    active = s[:n] - b[:n]
    active = active[~np.isnan(active)]
    if len(active) == 0:
        return 0.0
    ann_active = float(active.mean() * TRADING_DAYS)
    te = float(active.std() * np.sqrt(TRADING_DAYS))
    return ann_active / te if te > 0 else 0.0


# ── Tail ratio ────────────────────────────────────────────────────────────

def tail_ratio(returns: np.ndarray | pd.Series,
               percentile: float = 5.0) -> float:
    """Ratio of right-tail magnitude to left-tail magnitude.

    tail_ratio = |P(100 − percentile)| / |P(percentile)|

    A tail ratio > 1 means the right tail is larger (good asymmetry).
    Inspired by Seides (2015) and AQR's "expected tail ratio".

    Args:
        returns    : Daily return series.
        percentile : Tail size in percent (5 → 5th and 95th percentiles).

    Returns:
        Tail ratio ≥ 0.
    """
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    right = abs(np.percentile(r, 100 - percentile))
    left = abs(np.percentile(r, percentile))
    return float(right / left) if left > 0 else 0.0


# ── Sharpe helper (consistent with backtest/evaluation) ───────────────────

def _sharpe(returns: np.ndarray | pd.Series) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def _max_dd(returns: np.ndarray | pd.Series) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    cum = np.cumprod(1 + r)
    running_max = np.maximum.accumulate(cum)
    return float(-(((cum - running_max) / running_max).min()))


# ── Comprehensive report ──────────────────────────────────────────────────

def comprehensive_risk_report(strategy_returns: np.ndarray | pd.Series,
                               benchmark_returns: np.ndarray | pd.Series | None = None,
                               alpha: float = 0.05,
                               omega_threshold: float = 0.0,
                               tail_percentile: float = 5.0) -> dict:
    """All risk metrics in one dict.

    Args:
        strategy_returns  : Daily strategy return series.
        benchmark_returns : Daily benchmark returns (for IR). Optional.
        alpha             : CVaR tail probability.
        omega_threshold   : Omega ratio threshold return per day.
        tail_percentile   : Percentile for tail ratio.

    Returns:
        Dict with keys: sharpe, cvar_daily, cvar_ann, omega, calmar,
        information_ratio, tail_ratio, max_dd.
        information_ratio is None if benchmark_returns is None.
    """
    s = np.asarray(strategy_returns)
    s = s[~np.isnan(s)]

    report = {
        "sharpe":      round(_sharpe(s), 4),
        "cvar_daily":  round(cvar(s, alpha), 4),
        "cvar_ann":    round(cvar_annualised(s, alpha), 4),
        "omega":       round(omega_ratio(s, omega_threshold), 4),
        "calmar":      round(calmar_ratio(s), 4),
        "tail_ratio":  round(tail_ratio(s, tail_percentile), 4),
        "max_dd":      round(_max_dd(s), 4),
        "information_ratio": None,
    }

    if benchmark_returns is not None:
        b = np.asarray(benchmark_returns)
        b = b[~np.isnan(b)]
        report["information_ratio"] = round(information_ratio(s, b), 4)

    return report
