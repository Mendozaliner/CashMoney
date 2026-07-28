"""Defensive Dual-Asset Cash Sleeve (session 23, E34).

When v2's equity trend signal is OFF (SPY below SMA200 band), the strategy
normally earns only T-bill rate on idle cash. This module allocates defensive
cash between TWO independently-trend-gated assets: IEF (intermediate bonds)
and GLD (gold) using fixed proportions gated by their own SMA trend checks.

Philosophy (Harry Browne / All-Season / Ilmanen 2011):
- BONDS (IEF) rally in recession / deflation / risk-off environments (2008-09).
- GOLD (GLD) rallies in inflation / currency-debasement environments (2022).
- Holding BOTH defensive assets (when each is in its own uptrend) provides
  more consistent bear-market protection across different macro regimes than
  a single defensive asset (E33's IEF-only approach).

Key distinctions from prior experiments:
- E33 TB (s22): IEF-only defensive sleeve — tested SMA gate on IEF. FAILED CI.
  DDAS adds GLD as a second defensive asset; both are independently gated.
- E20 CTA (s12): three-way active rotation (SPY/IEF/GLD), trend-follows all.
  DDAS keeps the equity sleeve as PURE v2 — only the cash sleeve changes.
- E14 PP (s9): Harry Browne 25% fixed slots for all four assets simultaneously.
  DDAS activates IEF/GLD ONLY during v2 cash periods (35% of time historically).

Academic basis:
- Ilmanen (2011) "Expected Returns": bonds and gold serve as alternative
  hedges in different environments; both should be held in diversified
  defensive sleeves.
- Erb & Harvey (2013) JFE: gold provides inflation hedge and crisis hedge;
  conditional allocation based on economic regime is optimal.
- Asness, Moskowitz & Pedersen (2013) JF: trend following on bonds AND gold
  is independently profitable; combining both trend-following signals reduces
  drawdown without proportional return loss.
- Faber (2007) SSRN 962461: SMA trend timing improves risk-adjusted returns
  on both bonds and gold; gating prevents holding during trend reversals.

Risk scenario addressed:
- 2022 rising-rate bear market: IEF fell -18% while v2 was in cash equity.
  E33 partially protected via IEF SMA gate (IEF crossed below SMA200 ~Feb 2022).
  DDAS with GLD sleeve captures gold's relative strength in inflation regimes
  (GLD +0.4% in 2022 vs IEF -18%).

Tunable parameters (max 2): gld_frac, defense_window.
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

DEFAULTS = {"gld_frac": 0.50, "defense_window": 200}


def multi_signals(close: pd.Series,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  gld_frac: float = 0.50,
                  defense_window: int = 200,
                  target_vol: float = 0.18,
                  lookback: int = 20) -> pd.DataFrame:
    """Weight schedule for v2 (SPY) + dual defensive sleeve (IEF + GLD).

    Returns DataFrame with columns ['SPY', 'IEF', 'GLD'] where:
      SPY weight = v2 signal (unchanged)
      IEF weight = (1-gld_frac) * cash_avail * ief_trend_gate
      GLD weight = gld_frac * cash_avail * gld_trend_gate
    Residual cash (ungated or SMA gate OFF) earns T-bill rate.

    Each defensive asset is independently gated by its own SMA(defense_window).
    When a defensive asset is below its own SMA, that fraction stays in T-bills.

    Args:
        close          : SPY daily adjusted close.
        ief            : IEF daily adjusted close (loaded if None).
        gld            : GLD daily adjusted close (loaded if None).
        gld_frac       : Fraction of defensive cash allocated to GLD.
                         (1-gld_frac) goes to IEF. Both subject to their
                         own SMA trend gates.
        defense_window : SMA window for both IEF and GLD defensive gates.
        target_vol     : V2 annualized vol target (champion 0.18, fixed).
        lookback       : V2 realized-vol lookback days (champion 20, fixed).
    """
    spy_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)
    cash_avail = (1.0 - spy_sig).clip(0.0, 1.0)

    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]

    ief_a = ief.reindex(close.index, method="ffill")
    gld_a = gld.reindex(close.index, method="ffill")

    # Independent SMA trend gates for each defensive asset
    ief_gate = (ief_a > ief_a.rolling(defense_window).mean()).astype(float).shift(1).fillna(0.0)
    gld_gate = (gld_a > gld_a.rolling(defense_window).mean()).astype(float).shift(1).fillna(0.0)

    # Defensive allocations: each gated independently
    ief_weight = cash_avail * (1.0 - gld_frac) * ief_gate
    gld_weight = cash_avail * gld_frac * gld_gate

    return pd.DataFrame(
        {"SPY": spy_sig, "IEF": ief_weight, "GLD": gld_weight},
        index=close.index,
    )
