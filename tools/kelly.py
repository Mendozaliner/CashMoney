"""Kelly Criterion position sizing toolkit.

Implements several formulations of Kelly-optimal bet sizing, ranging from
the classical full-Kelly through to the practical fractional-Kelly variants
used by real trading desks.

Philosophy (Ed Thorp, 1962 & 2008):
  The Kelly criterion maximises the long-run compound growth rate of a
  portfolio. Full Kelly maximises E[log(W)] and is the theoretically
  'correct' answer under the log-utility assumption. In practice, desks
  use half-Kelly (or lower) because:
    1. Return estimates are noisy; over-betting on a wrong estimate is
       catastrophic (Haghani & Dewey 2016 — the Dueling experiment).
    2. Full-Kelly produces extreme drawdowns (~50% max DD expected).
    3. Half-Kelly gives ~75% of growth with far lower variance.

Relationship to CashMoney's vol-target champion (v2):
  v2's exposure = min(1, 0.18 / σ) is equivalent to a fractional-Kelly
  rule where the fraction is chosen so that the expected turnover (and
  hence path-dependency cost) is bounded. The Kelly calculator below
  makes this equivalence explicit so future experiments can be designed
  around explicit Kelly fractions rather than arbitrary vol targets.

References:
  - Kelly, J.L. (1956). A New Interpretation of Information Rate. BSTJ.
  - Thorp, E.O. (1962). Beat the Dealer. (Appendix).
  - Thorp, E.O. (2008). The Kelly Criterion in Blackjack, Sports Betting,
    and the Stock Market. Handbook of Asset and Liability Management.
  - Haghani, V. & Dewey, R. (2016). Rational Decision-Making Under
    Uncertainty. SSRN 2856963.
  - MacLean, Thorp & Ziemba (2011). The Kelly Capital Growth Investment
    Criterion. World Scientific.
"""
from __future__ import annotations
import math


def continuous_kelly(mu: float, sigma: float) -> float:
    """Full Kelly fraction for a continuous log-normal return process.

    f* = μ / σ²   (Thorp 2008, eq. 7)

    Args:
        mu    : Expected daily (or per-period) return, e.g. 0.0004.
        sigma : Daily (or per-period) volatility, e.g. 0.012.

    Returns:
        Optimal fraction of wealth to invest (can exceed 1.0 = leverage).
        Caller is responsible for capping at the leverage limit.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    return mu / (sigma ** 2)


def sharpe_kelly(sharpe_annualised: float,
                 sigma_annualised: float) -> float:
    """Full Kelly from an annualised Sharpe ratio.

    The Sharpe S = μ_ann / σ_ann, so f* = S / σ_ann.
    This is the form most natural for strategy backtests.

    Args:
        sharpe_annualised : Observed annualised Sharpe ratio.
        sigma_annualised  : Annualised return volatility (e.g. 0.15 = 15%).

    Returns:
        Full Kelly fraction.
    """
    if sigma_annualised <= 0:
        raise ValueError(f"sigma_annualised must be positive, got {sigma_annualised}")
    return sharpe_annualised / sigma_annualised


def fractional_kelly(full_kelly: float, fraction: float = 0.5,
                     leverage_cap: float = 1.0) -> float:
    """Apply a fractional discount to the full Kelly.

    Half-Kelly (fraction=0.5) is the industry standard for stock/ETF
    strategies where Sharpe estimates have high estimation error.
    A quarter-Kelly is common in commodities trend-following.

    Args:
        full_kelly    : Full Kelly fraction from continuous_kelly() or
                        sharpe_kelly().
        fraction      : Kelly fraction to use (0 < fraction <= 1).
        leverage_cap  : Hard cap on the resulting position (default 1.0 =
                        no leverage, matching the CashMoney G1 guardrail).

    Returns:
        Fractional Kelly allocation, capped at leverage_cap.
    """
    if not 0 < fraction <= 1:
        raise ValueError(f"fraction must be in (0, 1], got {fraction}")
    return min(full_kelly * fraction, leverage_cap)


def kelly_growth_rate(mu: float, sigma: float, fraction: float) -> float:
    """Expected long-run compound growth rate under fractional-Kelly.

    g(f) = f*μ - ½*f²*σ²   (continuous approximation; Thorp 2008, eq. 9)

    This lets you compare growth rates across different fraction choices
    and see the diminishing returns of pushing beyond half-Kelly.

    Args:
        mu       : Per-period expected return.
        sigma    : Per-period volatility.
        fraction : The bet size (fraction of wealth invested).

    Returns:
        Expected log-growth rate per period.
    """
    return fraction * mu - 0.5 * (fraction ** 2) * (sigma ** 2)


def kelly_summary(sharpe_annualised: float,
                  sigma_annualised: float,
                  leverage_cap: float = 1.0) -> dict:
    """Full Kelly analysis for a strategy, including the growth-rate surface.

    Returns a dict with full-Kelly, half-Kelly, quarter-Kelly fractions
    and their expected growth rates, making the tradeoff legible at a glance.

    Args:
        sharpe_annualised : Annualised Sharpe ratio of the strategy.
        sigma_annualised  : Annualised volatility of the strategy returns.
        leverage_cap      : Hard cap on leverage (default 1.0).

    Returns:
        Dict with 'full', 'half', 'quarter' fractions and growth rates.
    """
    td = 252
    mu_daily = sharpe_annualised * sigma_annualised / td
    sigma_daily = sigma_annualised / math.sqrt(td)

    full = sharpe_kelly(sharpe_annualised, sigma_annualised)
    full_capped = min(full, leverage_cap)

    fractions = {"full": 1.0, "half": 0.5, "quarter": 0.25}
    result = {
        "full_kelly": round(full, 4),
        "full_kelly_capped": round(full_capped, 4),
        "leverage_cap": leverage_cap,
        "sharpe": sharpe_annualised,
        "sigma_ann": sigma_annualised,
        "fractions": {},
    }

    for name, frac in fractions.items():
        f = fractional_kelly(full, fraction=frac, leverage_cap=leverage_cap)
        g_daily = kelly_growth_rate(mu_daily, sigma_daily, f)
        g_ann = g_daily * td
        result["fractions"][name] = {
            "fraction_of_kelly": frac,
            "position": round(f, 4),
            "growth_rate_ann": round(g_ann * 100, 3),
        }

    return result


def vol_target_to_kelly_equiv(vol_target: float,
                               sharpe_annualised: float) -> float:
    """Express a vol-targeting rule as its implied Kelly fraction.

    v2's rule: f = min(1, vol_target / σ) is equivalent to choosing a
    Kelly fraction such that the sizing equals f* when σ = vol_target:
        implied_kelly_fraction = vol_target * sharpe / 1

    This helper makes the implicit Kelly assumption of vol_target explicit.

    Args:
        vol_target        : The vol-targeting volatility ceiling (e.g. 0.18).
        sharpe_annualised : The strategy's estimated Sharpe ratio.

    Returns:
        Implied Kelly fraction the vol-target rule is betting at vol_target.
    """
    full = sharpe_kelly(sharpe_annualised, vol_target)
    return min(1.0 / full, 1.0) if full > 0 else 0.0
