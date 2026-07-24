"""VIX-Regime Dynamic Ensemble (session 20, E29).

Philosophy: Market regimes dictate which strategy family adds the most value.
Three regimes detected via the CBOE VIX fear gauge:

  LOW VIX (<20):       Bull trending market  → pure v2 (SMA200 + vol-target)
  ELEVATED VIX (20-30): Choppy/uncertain     → blend v2 + Bollinger mean reversion
  CRISIS VIX (>30):    Bear/panic market     → CTA multi-asset (bonds + gold crisis alpha)

Key innovation vs E22 (fixed-weight ensemble, s13): weights are DYNAMIC based
on VIX regime, not fixed. This eliminates CTA's bull-market drag (the E22 failure
mode: OOS corr 0.943 because CTA-SPY duplicated v2-SPY in bull runs) by only
using CTA when the equity trend has broken down and crisis protection is needed.

Academic basis:
- Ang & Bekaert (2002) "International Asset Allocation with Regime Shifts": time-
  varying correlations between regime states; single-regime allocation is sub-optimal.
- Guidolin & Timmermann (2008) RFS: regime-switching models beat static allocation.
- Whaley (2009) JDM: VIX is the 'investor fear gauge' — regimes map to VIX quantiles.
- AQR (2020): CTA provides 'crisis alpha' precisely when equity trend-following
  stalls; dynamic activation avoids the bull-market performance drag.

Timing contract: VIX at close-t and price signals at close-t fill at close-t+1.
All signals use only historical data through bar-t (no lookahead).
"""
import numpy as np
import pandas as pd

from strategies import vol_target, mean_reversion, cta_trend

TRADING_DAYS = 252


def multi_signals(price_panel: pd.DataFrame,
                  vix: pd.Series,
                  vix_elevated: float = 20.0,
                  vix_crisis: float = 30.0,
                  w_v2_elevated: float = 0.60,
                  w_bol_elevated: float = 0.40,
                  target_vol: float = 0.18,
                  bol_k: float = 2.5,
                  cta_vol: float = 0.12) -> pd.DataFrame:
    """Dynamic regime-based portfolio weights.

    Args:
        price_panel   : Wide Close DataFrame (date x ticker); must contain 'SPY'.
                        IEF and GLD used in crisis mode if present.
        vix           : Daily VIX close series (any DatetimeIndex; aligned internally).
        vix_elevated  : VIX threshold for elevated regime (default 20).
        vix_crisis    : VIX threshold for crisis regime (default 30).
        w_v2_elevated : v2 weight in elevated regime (default 0.60).
        w_bol_elevated: Bollinger MR weight in elevated regime (default 0.40).
        target_vol    : Annualized vol target for the v2 sleeve.
        bol_k         : Bollinger band width in std-dev (default 2.5, from E18 best).
        cta_vol       : Per-asset vol target for CTA sleeve (default 0.12, E20 best).

    Returns:
        weights : DataFrame (date x ['SPY', 'IEF', 'GLD']), row sums <= 1.0.
                  Compatible with backtest.multi_engine.portfolio_returns().

    No-lookahead guarantee: VIX at close-t, SMA/rv computed through bar-t.
    The shift(2) in multi_engine translates this to fill at t+1 → return t+1→t+2.
    """
    spy = price_panel["SPY"]

    # Align VIX to price panel trading dates; forward-fill weekends/holidays
    vix_aligned = vix.reindex(price_panel.index).ffill().fillna(20.0)

    # Regime indicators (bool → float for arithmetic)
    normal   = (vix_aligned < vix_elevated).astype(float)
    elevated = ((vix_aligned >= vix_elevated) &
                (vix_aligned < vix_crisis)).astype(float)
    crisis   = (vix_aligned >= vix_crisis).astype(float)

    # Sub-strategy signals
    v2_sig  = vol_target.signals(spy, target_vol=target_vol, lookback=20)
    bol_sig = mean_reversion.bollinger_signals(spy, k=bol_k, exit_at="upper_half")

    cta_assets = [c for c in ["SPY", "IEF", "GLD"] if c in price_panel.columns]
    cta_w = cta_trend.multi_signals(
        price_panel[cta_assets],
        assets=cta_assets,
        vol_target=cta_vol,
        normalize=False,
    )

    # Build combined weight matrix
    combined = pd.DataFrame(0.0, index=price_panel.index,
                            columns=["SPY", "IEF", "GLD"])

    # Normal regime: pure v2 in SPY
    combined["SPY"] += normal * v2_sig

    # Elevated regime: v2 + Bollinger blend in SPY
    combined["SPY"] += elevated * (w_v2_elevated * v2_sig +
                                   w_bol_elevated * bol_sig)

    # Crisis regime: CTA multi-asset (bonds + gold may surge as equities crash)
    for col in cta_assets:
        if col in combined.columns and col in cta_w.columns:
            combined[col] = combined[col] + crisis * cta_w[col]

    return combined.clip(0.0, 1.0)
