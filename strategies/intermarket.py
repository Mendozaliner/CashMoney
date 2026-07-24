"""Inter-Market Risk Filter: Bond-Equity Relative Strength (session 20, E30).

Philosophy: In healthy equity bull markets, stocks outperform bonds. When bonds
OUTPERFORM equities over a multi-month horizon, it signals a 'flight to quality'
that often precedes or coincides with equity drawdowns. This filter uses
bond-vs-equity relative momentum as a risk warning overlay on v2.

Academic basis:
- Murphy (1991) "Intermarket Technical Analysis": equities, bonds, commodities,
  and currencies are interconnected; bond trends lead equity trends.
- Asness, Moskowitz, Pedersen (2013) JF "Value and Momentum Everywhere":
  cross-asset momentum is persistent; relative momentum identifies risk regimes.
- Faber (2007) SSRN 962461: inter-asset momentum signals identify equity risk.
- Ilmanen (2011) "Expected Returns": when investors flee to bonds, the equity
  risk premium is compressing — a reliable signal of impending equity stress.

Key distinction from E3/E7 (dual momentum, CLOSED): Dual momentum ROTATED
capital to bonds when bonds beat equities. This filter only SCALES DOWN v2
exposure — it never switches into bonds. Avoids the TLT catastrophe of 2022
(where rotating to bonds would have hurt) while still capturing the warning signal.

Signal: SPY 3-month momentum vs IEF (7-10y Treasury) 3-month momentum.
  - SPY >= IEF: equity risk-on, no change to v2
  - SPY < IEF: flight to quality detected, scale v2 by reduced_scale

IEF chosen (vs TLT): 7-10y duration is less rate-sensitive than 20y TLT,
making the comparison more stable in rate-rising environments (2022).

Timing contract: signals use only data through bar-t; filled at bar t+1.
"""
import numpy as np
import pandas as pd

from strategies import vol_target

TRADING_DAYS = 252


def signals(spy: pd.Series,
            ief: pd.Series,
            target_vol: float = 0.18,
            lookback: int = 63,
            reduced_scale: float = 0.5) -> pd.Series:
    """Bond-equity relative strength overlay on v2.

    Args:
        spy          : SPY daily close prices.
        ief          : IEF daily close prices.
        target_vol   : Annualized vol target for base v2 signal.
        lookback     : Momentum lookback in trading days (default 63 ≈ 3 months).
        reduced_scale: Exposure multiplier when IEF beats SPY (default 0.5).

    Returns:
        SPY exposure signal in [0, 1].
    """
    base = vol_target.signals(spy, target_vol=target_vol, lookback=20)

    # Align IEF to SPY dates; forward-fill gaps (IEF starts 2002-07)
    ief_aligned = ief.reindex(spy.index).ffill()

    spy_mom = spy.pct_change(lookback)
    ief_mom = ief_aligned.pct_change(lookback)

    # Risk-on when equities outperform (or equal) bonds over lookback
    risk_on = (spy_mom >= ief_mom)

    # Scale v2: full exposure in risk-on, reduced_scale in risk-off
    scale = risk_on.astype(float) + (~risk_on).astype(float) * reduced_scale

    # Where IEF has no data yet (pre-2002), treat as risk-on (don't penalize)
    scale = scale.where(ief_mom.notna(), 1.0)

    return (base * scale).clip(0.0, 1.0)
