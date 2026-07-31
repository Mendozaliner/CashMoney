"""Real Earnings Growth Filter — Shiller macro overlay (session 25, E39).

Philosophy: Corporate earnings growth is the primary long-run driver of equity
returns. When real (inflation-adjusted) earnings are contracting on a 12-month
basis, the macro backdrop is deteriorating and equity risk is elevated. This
overlay reduces v2's exposure during confirmed earnings contractions.

The signal differs from E31 CAPE Value Tilt in a fundamental way:
  E31 used CAPE LEVEL (percentile rank): failed OOS because CAPE was ALWAYS
  above the 90th percentile during 2020-2025H (corr_v2=1.000 in OOS).
  This strategy uses the DIRECTION and RATE OF CHANGE of real earnings:
  earnings momentum varies meaningfully across all periods (including the
  2020-2025H OOS window: Q2-2022 real earnings fell ~8%; 2023-24 recovered
  strongly). The signal turns on/off at actual inflection points, not a
  static high-valuation regime.

Signal construction:
  1. Shiller monthly Earnings and CPI → real_earnings = Earnings / CPI * 100
  2. 12-month change: growth_12m = real_earnings / real_earnings.shift(12) - 1
  3. Shift 1 month (no-lookahead; data published with ~1-2 month lag)
  4. Forward-fill to daily calendar
  5. When growth_12m < growth_threshold: de-risk v2 by multiplying by de_risk_scale
     Otherwise: maintain full v2 signal

Key distinctions:
- E31 CAPE Tilt (s22): uses CAPE LEVEL percentile → always in top decile OOS.
  This uses earnings MOMENTUM direction → varies across all periods.
- E32 Yield Curve (CLOSED, s22): used bond ETF relative momentum → redundant
  with SMA200 gate at macro cycle frequency.
- The earnings signal is a LEADING macro indicator of equity risk, not a
  valuation-level anchor. It captures earnings recessions (2001, 2008, 2020,
  H2-2022) that coincide with equity drawdowns.

Academic basis:
- Novy-Marx (2013) JFE "The Other Side of Value": earnings quality and
  growth are stronger predictors of future returns than valuation levels.
- Chan, Jegadeesh & Lakonishok (1996) JF "Momentum of Earnings Announcement":
  earnings revisions and momentum predict stock returns; downward revisions
  precede negative excess returns.
- Fama & French (1989) JFE: expected returns are higher when the economy is
  weak and earnings growth is deteriorating.
- Koijen, Lustig & Van Nieuwerburgh (2017) JFE: dividend / earnings growth
  forecasts equity risk premium with out-of-sample power.
- Liew & Vassalou (2000) JFE: HML and SMB factor returns predict GDP growth;
  the link between earnings growth and equity risk is systematic.

Tunable parameters (max 2): growth_threshold (when to de-risk), de_risk_scale
(fraction of v2 exposure to keep during contraction).
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_shiller

DEFAULTS = {"growth_threshold": -0.05, "de_risk_scale": 0.5}


def _real_earnings_growth_daily(close_index: pd.DatetimeIndex) -> pd.Series:
    """Load Shiller monthly real earnings growth, forward-filled to daily.

    No-lookahead: shift(1) on the monthly series so the growth rate known
    after month M is applied starting at the first trading day of month M+1.
    """
    try:
        sh = load_shiller()
    except FileNotFoundError:
        return pd.Series(0.0, index=close_index, name="earnings_growth")

    if "Earnings" not in sh.columns or "Cpi" not in sh.columns:
        return pd.Series(0.0, index=close_index, name="earnings_growth")

    real_e = sh["Earnings"] / sh["Cpi"] * 100.0
    growth_12m = real_e / real_e.shift(12) - 1.0

    # Shift 1 period (1 month lag): data for month M available at month M+1
    growth_lagged = growth_12m.shift(1)

    # Reindex to daily trading calendar with forward-fill
    combined = growth_lagged.reindex(
        growth_lagged.index.union(close_index)
    ).sort_index().ffill()
    return combined.reindex(close_index).fillna(0.0).rename("earnings_growth")


def signals(close: pd.Series,
            growth_threshold: float = -0.05,
            de_risk_scale: float = 0.5,
            target_vol: float = 0.18,
            lookback: int = 20) -> pd.Series:
    """V2 signal scaled down when real Shiller earnings are contracting.

    Args:
        close            : SPY daily adjusted close.
        growth_threshold : 12-month real earnings growth rate below which to
                           apply the de-risk scale (e.g. -0.05 = -5% y/y).
        de_risk_scale    : Fraction of v2 exposure to hold during contraction
                           (e.g. 0.5 = cut v2 to 50% when earnings fall 5+%).
        target_vol       : V2 volatility target (champion 0.18, fixed).
        lookback         : V2 realized-vol lookback in days (champion 20, fixed).

    Returns:
        Exposure series in [0, 1], same index as close.
        Equal to v2 when earnings are growing (or data unavailable).
        Equal to v2 * de_risk_scale when earnings are contracting.
    """
    v2_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)
    eg = _real_earnings_growth_daily(close.index)

    contracting = (eg < growth_threshold).astype(float)
    multiplier  = 1.0 - contracting * (1.0 - de_risk_scale)
    return (v2_sig * multiplier).clip(0.0, 1.0)
