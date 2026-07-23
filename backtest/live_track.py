"""Live-track monthly graduation checkpoints (Phase 2).

Zero-config engineering module (s19, 2026-07-23). Computes, from
portfolio.json history alone, the numbers the Phase-2 graduation review
needs, so the August review is mechanical rather than ad-hoc:

- month-by-month live portfolio vs SPY returns since the live baseline
  (2026-07-14 clock start per STATE.md);
- consecutive-months-of-outperformance counter (criterion 2);
- worst live drawdown to date (criterion 3);
- PSR-based Minimum Track Record Length (MinTRL) estimate: how many live
  observations are needed before a positive live Sharpe is statistically
  distinguishable from zero (Bailey & Lopez de Prado 2012, "The Sharpe
  Ratio Efficient Frontier"; see also the Deflated Sharpe Ratio, 2014).

References
----------
- Bailey, D.H., Lopez de Prado, M. (2012). The Sharpe Ratio Efficient
  Frontier. Journal of Risk 15(2). SSRN 1821643.
- Bailey, D.H., Lopez de Prado, M. (2014). The Deflated Sharpe Ratio.
  Journal of Portfolio Management 40(5). SSRN 2460551.
- Portfolio Optimizer blog: "The Probabilistic Sharpe Ratio: ...
  Minimum Track Record Length" (accessed 2026-07-23).

Reporting only: this module never trades, never rebalances, and never
touches the frozen champion.
"""
from __future__ import annotations

import math
from collections import OrderedDict


def daily_marks(portfolio: dict) -> "OrderedDict[str, float]":
    """Collapse portfolio.json history to one value per mark_date.

    Multiple sessions can mark the same trading day (carried marks); the
    LAST entry for a mark_date wins. Marks are returned sorted by date.
    Entries before the live baseline date are included so callers can
    slice as needed.
    """
    marks: dict[str, float] = {}
    for h in portfolio.get("history", []):
        d = h.get("mark_date") or h.get("date")
        v = h.get("value")
        if d is None or v is None:
            continue
        marks[d] = float(v)
    return OrderedDict(sorted(marks.items()))


def monthly_checkpoints(portfolio: dict, spy_closes: "dict[str, float]",
                        baseline_date: str = "2026-07-13") -> list:
    """Month-by-month live vs SPY performance since the baseline.

    spy_closes: mapping date-str -> SPY close (completed days only).
    A month is included only once it is COMPLETE (a later-month mark
    exists); the in-progress month is reported separately by summary().
    Returns a list of dicts: month, port_ret, spy_ret, beat (bool).
    """
    marks = daily_marks(portfolio)
    marks = OrderedDict((d, v) for d, v in marks.items() if d >= baseline_date)
    if len(marks) < 2:
        return []
    dates = list(marks)
    months: "OrderedDict[str, list]" = OrderedDict()
    for d in dates:
        months.setdefault(d[:7], []).append(d)
    out = []
    month_keys = list(months)
    prev_end = dates[0]  # baseline mark
    for i, m in enumerate(month_keys):
        is_last = (i == len(month_keys) - 1)
        end = months[m][-1]
        if is_last:
            break  # in-progress month: not a completed checkpoint
        if end == prev_end:
            continue  # baseline month with no post-baseline marks
        p0, p1 = marks[prev_end], marks[end]
        s0 = spy_closes.get(prev_end)
        s1 = spy_closes.get(end)
        port_ret = p1 / p0 - 1.0
        spy_ret = (s1 / s0 - 1.0) if (s0 and s1) else None
        out.append({
            "month": m,
            "window": (prev_end, end),
            "port_ret": port_ret,
            "spy_ret": spy_ret,
            "beat": (spy_ret is not None and port_ret > spy_ret),
        })
        prev_end = end
    return out


def consecutive_beats(checkpoints: list) -> int:
    """Consecutive completed months of outperformance, counted from the end."""
    n = 0
    for cp in reversed(checkpoints):
        if cp.get("beat"):
            n += 1
        else:
            break
    return n


def worst_drawdown(portfolio: dict, baseline_date: str = "2026-07-13") -> float:
    """Worst peak-to-trough drawdown of the live track (negative fraction)."""
    marks = daily_marks(portfolio)
    peak, worst = -math.inf, 0.0
    for d, v in marks.items():
        if d < baseline_date:
            continue
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1.0)
    return worst


def min_track_record_length(returns, sr_benchmark: float = 0.0,
                            confidence: float = 0.95) -> float:
    """PSR-based Minimum Track Record Length (Bailey & LdP 2012).

    MinTRL = 1 + [1 - g3*SR + (g4-1)/4 * SR^2] * (z_c / (SR - SR*))^2
    where SR is the observed per-period Sharpe, g3 skewness, g4 kurtosis
    (non-excess), SR* the benchmark per-period Sharpe, z_c the normal
    quantile at the requested confidence. Returns the number of
    observations (same frequency as `returns`) needed; inf if SR <= SR*.
    """
    xs = [float(x) for x in returns]
    n = len(xs)
    if n < 3:
        return float("inf")
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return float("inf")
    sr = mu / sd
    if sr <= sr_benchmark:
        return float("inf")
    g3 = sum((x - mu) ** 3 for x in xs) / (n * sd ** 3)
    g4 = sum((x - mu) ** 4 for x in xs) / (n * sd ** 4)
    # normal quantile via inverse error function
    z = math.sqrt(2.0) * _erfinv(2.0 * confidence - 1.0)
    return 1.0 + (1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2) * (z / (sr - sr_benchmark)) ** 2


def _erfinv(y: float) -> float:
    """Winitzki approximation of the inverse error function (|err|<2e-3)."""
    a = 0.147
    ln = math.log(1.0 - y * y)
    t1 = 2.0 / (math.pi * a) + ln / 2.0
    return math.copysign(math.sqrt(math.sqrt(t1 * t1 - ln / a) - t1), y)


def summary(portfolio: dict, spy_closes: "dict[str, float]",
            baseline_date: str = "2026-07-13",
            required_months: int = 3, dd_limit: float = -0.20) -> dict:
    """One-call Phase-2 scoreboard for reports and briefings."""
    cps = monthly_checkpoints(portfolio, spy_closes, baseline_date)
    marks = daily_marks(portfolio)
    live = [(d, v) for d, v in marks.items() if d >= baseline_date]
    diffs = []
    for (d0, v0), (d1, v1) in zip(live, live[1:]):
        s0, s1 = spy_closes.get(d0), spy_closes.get(d1)
        if s0 and s1:
            diffs.append((v1 / v0 - 1.0) - (s1 / s0 - 1.0))
    dd = worst_drawdown(portfolio, baseline_date)
    beats = consecutive_beats(cps)
    return {
        "completed_months": len(cps),
        "checkpoints": cps,
        "consecutive_beat_months": beats,
        "criterion2_pass": beats >= required_months,
        "worst_live_drawdown": dd,
        "criterion3_pass": dd > dd_limit,
        "live_obs": len(live),
        "min_trl_days_vs_spy": min_track_record_length(diffs) if diffs else float("inf"),
        "next_checkpoint": "first session after each calendar month completes",
    }
