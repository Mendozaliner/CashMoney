"""Comprehensive Drawdown Analytics and Risk-of-Ruin Tool.

Drawdown analysis goes beyond the MaxDD summary statistic to expose the
texture of a strategy's underwater experience: how often it goes underwater,
for how long, how deep, and how quickly it recovers. Ed Thorp's risk-of-ruin
formula provides a principled answer to "what's the probability the strategy
loses X% before gaining Y%?"

Philosophies implemented:
  - Ed Thorp (1962, 2008): Kelly Criterion + Risk of Ruin. The probability of
    ruin under a log-normal return process is analytically tractable; it depends
    on the expected excess return, volatility, and the drawdown tolerance.
  - Markowitz (1952): Semivariance as a better risk measure than variance —
    only downside deviations matter for the investor.
  - Bailey & Lopez de Prado (2012): Minimum Track Record Length (used in
    live_track.py) and the relationship between Sharpe, skew, and drawdown.

References
----------
Thorp, E.O. (1962). Beat the Dealer. Random House. Appendix.
Thorp, E.O. (2008). The Kelly Criterion in Blackjack, Sports Betting,
  and the Stock Market. Handbook of Asset and Liability Management.
Magdon-Ismail, M. & Atiya, A.F. (2004). Maximum Drawdown. Risk Magazine.
Bailey, D.H. & Lopez de Prado, M. (2012). The Sharpe Ratio Efficient Frontier.
  J. Risk 15(2).
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from typing import NamedTuple


class UnderwaterPeriod(NamedTuple):
    start: pd.Timestamp
    end: pd.Timestamp | None
    depth_pct: float
    duration_days: int


def equity_curve(returns: np.ndarray | pd.Series,
                 initial: float = 1.0) -> pd.Series:
    """Compound equity curve from a daily return series.

    Args:
        returns : Daily arithmetic returns (e.g. 0.01 = 1% gain).
        initial : Starting portfolio value.

    Returns:
        pd.Series of cumulative portfolio value.
    """
    r = pd.Series(returns) if not isinstance(returns, pd.Series) else returns
    return initial * (1 + r).cumprod()


def underwater_periods(returns: np.ndarray | pd.Series,
                       threshold_pct: float = 0.0) -> list[UnderwaterPeriod]:
    """Identify all underwater (drawdown) periods.

    An underwater period starts when the equity curve falls below a previous
    peak and ends when it recovers to or above that peak.

    Args:
        returns       : Daily arithmetic returns.
        threshold_pct : Minimum depth to report (default 0.0 = any DD).

    Returns:
        List of UnderwaterPeriod named tuples, ordered by start date.
    """
    eq = equity_curve(returns)
    peak = eq.expanding().max()
    dd = eq / peak - 1.0

    in_dd = False
    period_start = None
    period_start_pos: int = 0
    period_low: float = 0.0
    has_timestamps = isinstance(dd.index, pd.DatetimeIndex)

    periods: list[UnderwaterPeriod] = []

    for pos, (date, d) in enumerate(dd.items()):
        if not in_dd:
            if d < 0:
                in_dd = True
                period_start = date
                period_start_pos = pos
                period_low = d
        else:
            if d < period_low:
                period_low = d
            if d >= 0:
                if has_timestamps:
                    dur = (date - period_start).days + 1
                else:
                    dur = pos - period_start_pos + 1
                if abs(period_low) * 100 >= threshold_pct:
                    periods.append(UnderwaterPeriod(
                        start=period_start,
                        end=date,
                        depth_pct=round(period_low * 100, 2),
                        duration_days=dur,
                    ))
                in_dd = False
                period_start = None
                period_low = 0.0

    if in_dd and period_start is not None:
        last_date = dd.index[-1]
        if has_timestamps:
            dur = (last_date - period_start).days + 1
        else:
            dur = len(dd) - period_start_pos
        if abs(period_low) * 100 >= threshold_pct:
            periods.append(UnderwaterPeriod(
                start=period_start,
                end=None,
                depth_pct=round(period_low * 100, 2),
                duration_days=dur,
            ))

    return periods


def drawdown_stats(returns: np.ndarray | pd.Series) -> dict:
    """Comprehensive drawdown statistics.

    Args:
        returns : Daily arithmetic return series.

    Returns:
        Dict with max, average, median drawdown depths and durations.
    """
    periods = underwater_periods(returns, threshold_pct=0.5)
    eq = equity_curve(returns)
    running_dd = eq / eq.expanding().max() - 1.0

    if not periods:
        return {
            "n_drawdown_periods": 0,
            "max_drawdown_pct": 0.0,
            "avg_drawdown_pct": 0.0,
            "median_drawdown_pct": 0.0,
            "avg_duration_days": 0,
            "max_duration_days": 0,
            "avg_recovery_days": 0,
            "pct_time_underwater": 0.0,
            "calmar_proxy": float("inf"),
        }

    depths = [abs(p.depth_pct) for p in periods]
    durations = [p.duration_days for p in periods]
    closed = [p for p in periods if p.end is not None]
    recovery_days = [p.duration_days for p in closed]

    cagr = float(
        (eq.iloc[-1] / eq.iloc[0]) ** (252 / max(len(eq), 1)) - 1
    ) * 100
    calmar = cagr / max(depths) if depths else float("inf")

    pct_underwater = float((running_dd < 0).mean()) * 100

    return {
        "n_drawdown_periods": len(periods),
        "max_drawdown_pct": round(-max(depths), 2),
        "avg_drawdown_pct": round(-float(np.mean(depths)), 2),
        "median_drawdown_pct": round(-float(np.median(depths)), 2),
        "avg_duration_days": round(float(np.mean(durations)), 1),
        "max_duration_days": int(max(durations)),
        "avg_recovery_days": round(float(np.mean(recovery_days)), 1) if recovery_days else None,
        "pct_time_underwater": round(pct_underwater, 1),
        "calmar_proxy": round(calmar, 3),
    }


def semivariance(returns: np.ndarray | pd.Series,
                 threshold: float = 0.0,
                 annualise: bool = True) -> float:
    """Markowitz (1959) semivariance — downside risk measure.

    Only counts deviations below ``threshold`` (default 0 = any loss).
    Semideviation = sqrt(semivariance) gives a downside-only volatility.

    Args:
        returns    : Daily arithmetic returns.
        threshold  : Only count returns below this level.
        annualise  : Multiply by sqrt(252) for annual equivalent.

    Returns:
        Semideviation (not variance) for comparability with normal std.
    """
    r = np.asarray(returns)
    below = r[r < threshold] - threshold
    sv = float(np.mean(below ** 2)) if len(below) > 0 else 0.0
    semi_dev = math.sqrt(sv)
    return semi_dev * math.sqrt(252) if annualise else semi_dev


def risk_of_ruin(mu_annual: float,
                 sigma_annual: float,
                 ruin_threshold_pct: float = 20.0,
                 horizon_years: float = 5.0) -> float:
    """Ed Thorp probability-of-ruin estimate under log-normal returns.

    Uses the Gambler's Ruin approximation for a log-normal return process
    (Thorp 2008, eq. 20). Gives the probability that the portfolio suffers
    a cumulative peak-to-trough drawdown of at least `ruin_threshold_pct`
    percent over `horizon_years` years.

    Mathematical basis:
        For a Brownian motion with drift μ and volatility σ (continuously
        compounded returns), the probability that the process reaches a
        barrier at level -d (where d > 0) before a terminal time T is:

        P(ruin) ≈ Φ((-d - m*T) / (σ√T)) + exp(-2*m*d/σ²) * Φ((−d + m*T)/(σ√T))

    where m = μ - σ²/2 (the geometric mean drift), d = ln(1 + d_pct/100),
    and Φ is the standard normal CDF. This assumes continuous trading and a
    single absorbing barrier — an approximation that understates risk for
    discrete daily returns.

    Args:
        mu_annual           : Expected annualised arithmetic return (e.g. 0.09).
        sigma_annual        : Annualised return volatility (e.g. 0.12).
        ruin_threshold_pct  : The drawdown level that constitutes "ruin" (e.g. 20.0 for 20%).
        horizon_years       : Time horizon in years (e.g. 5.0).

    Returns:
        Probability of hitting the ruin threshold (0 to 1).

    Warning:
        This is an approximation for continuous log-normal returns.
        Real discrete returns have fatter tails; the true probability is higher.
        Use this as a lower-bound estimate.
    """
    from scipy.stats import norm

    if sigma_annual <= 0:
        return 0.0 if mu_annual > 0 else 1.0

    d = math.log(1.0 + ruin_threshold_pct / 100.0)
    m = mu_annual - 0.5 * sigma_annual ** 2
    T = horizon_years
    sigma_sqrt_T = sigma_annual * math.sqrt(T)

    if sigma_sqrt_T < 1e-12:
        return 1.0 if m < 0 else 0.0

    z1 = (-d - m * T) / sigma_sqrt_T
    z2 = (-d + m * T) / sigma_sqrt_T

    exponent = -2.0 * m * d / (sigma_annual ** 2)
    exponent = min(exponent, 700.0)

    prob = norm.cdf(z1) + math.exp(exponent) * norm.cdf(z2)
    return float(min(max(prob, 0.0), 1.0))


def ruin_surface(mu_annual: float,
                 sigma_annual: float,
                 thresholds: list[float] | None = None,
                 horizons: list[float] | None = None) -> pd.DataFrame:
    """Risk-of-ruin probability matrix across drawdown thresholds and horizons.

    Args:
        mu_annual    : Expected annual return.
        sigma_annual : Annual volatility.
        thresholds   : List of drawdown levels in percent (default: 10, 15, 20, 30, 50).
        horizons     : List of years (default: 1, 3, 5, 10, 20).

    Returns:
        DataFrame with thresholds as rows and horizons as columns.
    """
    thresholds = thresholds or [10, 15, 20, 30, 50]
    horizons = horizons or [1, 3, 5, 10, 20]

    data = {}
    for h in horizons:
        data[f"{h}yr"] = [
            round(risk_of_ruin(mu_annual, sigma_annual, t, h) * 100, 2)
            for t in thresholds
        ]

    return pd.DataFrame(data, index=[f"-{t}%" for t in thresholds])


def strategy_risk_report(returns: np.ndarray | pd.Series,
                          label: str = "strategy") -> dict:
    """Complete drawdown + ruin analysis for a return series.

    Args:
        returns : Daily arithmetic returns.
        label   : Strategy name for the report.

    Returns:
        Dict combining drawdown_stats(), semivariance, and risk_of_ruin.
    """
    r = np.asarray(returns)
    if len(r) == 0:
        return {}

    ann_ret = float((1 + r).prod() ** (252 / len(r)) - 1)
    ann_vol = float(np.std(r, ddof=1) * math.sqrt(252))

    dd_stats = drawdown_stats(r)
    semi_dev = semivariance(r)
    sortino = ann_ret / semi_dev if semi_dev > 0 else float("nan")

    ror_20pct_5yr = risk_of_ruin(ann_ret, ann_vol, ruin_threshold_pct=20.0,
                                  horizon_years=5.0)
    ror_20pct_10yr = risk_of_ruin(ann_ret, ann_vol, ruin_threshold_pct=20.0,
                                   horizon_years=10.0)
    ror_50pct_5yr = risk_of_ruin(ann_ret, ann_vol, ruin_threshold_pct=50.0,
                                  horizon_years=5.0)

    return {
        "label": label,
        "ann_return_pct": round(ann_ret * 100, 2),
        "ann_vol_pct": round(ann_vol * 100, 2),
        "semideviation_ann_pct": round(semi_dev * 100, 2),
        "sortino_proxy": round(sortino, 3),
        **dd_stats,
        "risk_of_ruin_20pct_5yr": round(ror_20pct_5yr * 100, 2),
        "risk_of_ruin_20pct_10yr": round(ror_20pct_10yr * 100, 2),
        "risk_of_ruin_50pct_5yr": round(ror_50pct_5yr * 100, 2),
    }
