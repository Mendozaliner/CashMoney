"""Statistical honesty layer for CashMoney (added 2026-07-14).

The research desk tests many configurations against the same history, so a good
backtest number is the *expected* outcome of luck, not evidence of skill. This
module makes the system disbelieve itself:

  * deflated_sharpe_ratio  -- discounts an observed Sharpe for the number of
    trials, the sample length, and non-normal returns (Bailey & Lopez de Prado,
    "The Deflated Sharpe Ratio", 2014). Returns the probability the TRUE Sharpe
    is > 0 after accounting for selection bias.
  * bootstrap_metric_ci / bootstrap_difference_ci -- resampling confidence
    intervals on a metric, and on the strategy-minus-benchmark difference, so a
    champion is only crowned when its edge clears the noise band.
  * after_tax_from_trades / buy_hold_after_tax / do_nothing_verdict -- answers
    the only question a personal investor actually cares about: "would I have
    done better, after tax, just holding the index?"

Pure stdlib + numpy; no scipy. Normal CDF / inverse-CDF via statistics.NormalDist.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist
import numpy as np
import pandas as pd

TRADING_DAYS = 252
_N = NormalDist()
_EULER = 0.5772156649015329


def _phi(x: float) -> float:
    return _N.cdf(x)


def _phi_inv(p: float) -> float:
    p = min(max(p, 1e-12), 1 - 1e-12)
    return _N.inv_cdf(p)


def sharpe_ratio(returns, periods: int = TRADING_DAYS, per_period: bool = False) -> float:
    """Annualized (default) or per-period Sharpe of a return series."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.std(ddof=1) == 0 or len(r) < 3:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    return sr if per_period else sr * np.sqrt(periods)


# --------------------------------------------------------------------------
# Deflated / Probabilistic Sharpe
# --------------------------------------------------------------------------
def probabilistic_sharpe_ratio(returns, sr_benchmark_pp: float = 0.0,
                               periods: int = TRADING_DAYS) -> float:
    """P(true Sharpe > benchmark) for one strategy, correcting for skew/kurtosis
    and sample length. sr_benchmark_pp is a PER-PERIOD Sharpe threshold."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    T = len(r)
    if T < 3 or r.std(ddof=1) == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)                     # per-period
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurt()) + 3.0           # pandas gives excess kurt
    denom = np.sqrt(1 - skew * sr + ((kurt - 1) / 4) * sr ** 2)
    if denom == 0:
        return 0.0
    return _phi((sr - sr_benchmark_pp) * np.sqrt(T - 1) / denom)


def expected_max_sharpe0(trial_sharpes_pp, n_trials: int | None = None) -> float:
    """Expected maximum per-period Sharpe achievable by chance across N trials
    (the benchmark SR0 in the Deflated Sharpe Ratio). trial_sharpes_pp is the
    set of per-period Sharpes actually observed across the grid."""
    s = np.asarray(trial_sharpes_pp, dtype=float)
    s = s[~np.isnan(s)]
    N = int(n_trials or len(s))
    if N < 2 or s.std(ddof=1) == 0:
        return 0.0
    v = s.std(ddof=1)
    return v * ((1 - _EULER) * _phi_inv(1 - 1.0 / N) +
                _EULER * _phi_inv(1 - 1.0 / (N * np.e)))


def deflated_sharpe_ratio(returns, trial_annual_sharpes,
                          periods: int = TRADING_DAYS) -> float:
    """Probability the selected strategy's TRUE Sharpe > 0, after deflating for
    the number of configurations tried. Feed EVERY trial's annualized Sharpe
    from the grid (including the winner). Adopt only if this is high (>=0.95)."""
    trials_pp = np.asarray(trial_annual_sharpes, dtype=float) / np.sqrt(periods)
    sr0 = expected_max_sharpe0(trials_pp, n_trials=len(trials_pp))
    return probabilistic_sharpe_ratio(returns, sr_benchmark_pp=sr0, periods=periods)


# --------------------------------------------------------------------------
# Bootstrap confidence intervals
# --------------------------------------------------------------------------
@dataclass
class CI:
    point: float
    lo: float
    hi: float
    p_le_zero: float          # share of resamples <= 0 (one-sided noise test)

    @property
    def clears_noise(self) -> bool:
        return bool(self.lo > 0.0)


def _metric_fn(name: str):
    name = name.lower()
    if name == "sharpe":
        return lambda r: sharpe_ratio(r)
    if name in ("cagr", "return", "mean"):
        return lambda r: float(np.nanmean(r)) * TRADING_DAYS
    raise ValueError(f"unknown metric {name!r}")


def bootstrap_metric_ci(returns, metric: str = "sharpe", n: int = 10000,
                        alpha: float = 0.05, seed: int = 0) -> CI:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    f = _metric_fn(metric)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n, len(r)))
    dist = np.array([f(r[i]) for i in idx])
    return CI(float(f(r)), float(np.quantile(dist, alpha / 2)),
              float(np.quantile(dist, 1 - alpha / 2)), float((dist <= 0).mean()))


def bootstrap_difference_ci(strategy_returns, benchmark_returns,
                            metric: str = "sharpe", n: int = 10000,
                            alpha: float = 0.05, seed: int = 0) -> CI:
    """CI on (strategy - benchmark) for the chosen metric, using PAIRED
    resampling of aligned rows so contemporaneous correlation is preserved.
    clears_noise == True means the edge is distinguishable from luck."""
    df = pd.concat([pd.Series(strategy_returns).rename("s"),
                    pd.Series(benchmark_returns).rename("b")], axis=1).dropna()
    s, b = df["s"].to_numpy(), df["b"].to_numpy()
    f = _metric_fn(metric)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(n, len(s)))
    diff = np.array([f(s[i]) - f(b[i]) for i in idx])
    return CI(float(f(s) - f(b)), float(np.quantile(diff, alpha / 2)),
              float(np.quantile(diff, 1 - alpha / 2)), float((diff <= 0).mean()))


# --------------------------------------------------------------------------
# After-tax reality check
# --------------------------------------------------------------------------
def after_tax_from_trades(trade_returns, holding_days,
                          st_rate: float = 0.35, lt_rate: float = 0.15,
                          principal: float = 1.0) -> float:
    """Terminal after-tax value of $principal run through a sequence of trades.
    Gains held < 365 days are taxed at st_rate, others at lt_rate; losses offset
    within the same tax bucket. A pragmatic approximation, not tax advice."""
    tr = np.asarray(trade_returns, dtype=float)
    hd = np.asarray(holding_days, dtype=float)
    equity = principal
    st_gain = lt_gain = 0.0
    for ret, days in zip(tr, hd):
        pnl = equity * ret
        equity += pnl
        if days < 365:
            st_gain += pnl
        else:
            lt_gain += pnl
    tax = max(st_gain, 0.0) * st_rate + max(lt_gain, 0.0) * lt_rate
    return equity - tax


def buy_hold_after_tax(price_returns, lt_rate: float = 0.15,
                       principal: float = 1.0) -> float:
    """Buy-and-hold defers all tax to a single long-term realization at the end."""
    r = np.asarray(price_returns, dtype=float)
    r = r[~np.isnan(r)]
    terminal = principal * float(np.prod(1 + r))
    gain = terminal - principal
    return terminal - max(gain, 0.0) * lt_rate


@dataclass
class DoNothingVerdict:
    strategy_after_tax: float
    hold_after_tax: float

    @property
    def strategy_wins(self) -> bool:
        return bool(self.strategy_after_tax > self.hold_after_tax)

    def __str__(self) -> str:
        edge = self.strategy_after_tax / self.hold_after_tax - 1
        who = "Strategy beats" if self.strategy_wins else "DOING NOTHING beats"
        return (f"{who} buy-and-hold after tax by {edge:+.1%} "
                f"(strat ${self.strategy_after_tax:.3f} vs hold "
                f"${self.hold_after_tax:.3f} per $1).")


def do_nothing_verdict(trade_returns, holding_days, benchmark_price_returns,
                       st_rate: float = 0.35, lt_rate: float = 0.15) -> DoNothingVerdict:
    """Would you have done better, after tax, just holding the benchmark?"""
    return DoNothingVerdict(
        after_tax_from_trades(trade_returns, holding_days, st_rate, lt_rate),
        buy_hold_after_tax(benchmark_price_returns, lt_rate),
    )
