"""Swensen Diversified 4-Asset Allocation (session 24, E37).

Philosophy (Swensen 2000 / 2009, "Pioneering Portfolio Management"):
Yale University CIO David Swensen pioneered portfolio construction based on
investing in TRULY DIFFERENT asset classes -- each driven by a distinct economic
risk premium -- rather than concentrating in stocks and bonds. The Yale
Endowment averaged 13.9% annual return over 20 years (1990-2009) by diversifying
across: equities, fixed income, real assets, private equity, and alternatives.

This module implements an ETF-based Swensen-inspired allocation using four LIQUID
and DIFFERENT asset classes, each independently trend-gated:

  SPY  -- US equity (equity risk premium)
  IEF  -- Intermediate bonds (duration risk premium / safe-haven)
  GLD  -- Gold (real asset / inflation + crisis hedge)
  [real_asset] -- Either VNQ (real estate) or DBC (commodity index)
                  VNQ: real estate risk premium (rent yield + property appreciation)
                  DBC: commodity risk premium (roll yield + inflation signal)

Each asset receives an equal 25% target weight, activated only when above its
own SMA(sma_window) trend gate. Cash fraction earns T-bill rate via rf_daily.

Key distinctions from prior experiments:
- E12 Risk Parity (SPY/IEF/GLD): INVERSE-VOL weighting, no real estate/commodities.
  Swensen alloc uses EQUAL weighting and different 4th asset.
- E14 Permanent Portfolio (SPY/TLT/GLD/SHY): FIXED weights with drift rebalancing.
  Swensen alloc uses TREND GATES that turn each position off below SMA.
- E10 GTAA-5 (SPY/EFA/DBC/VNQ/IEF): FIVE assets, 20% each. This uses 4 assets
  at 25% each, with a testable swap (VNQ vs DBC) for the real-asset slot.
- E6 GTAA-4 (SPY/IWM/IEF/GLD): different universe (no real assets outside GLD).

The hypothesis: Four TRULY UNCORRELATED economic premia -- equity, safe-haven,
gold/inflation, and real assets -- provide better diversification than any
single-family strategy while maintaining trend gates that prevent catastrophic
drawdowns (like the 2008 GFC or 2022 inflation shock that punished static 60/40).

Why the VNQ vs DBC parameterization:
- VNQ (real estate): Brounen & De Koning (2012) show REITs are a genuine
  diversifier with a real estate risk premium separate from equity and bonds.
- DBC (commodities): Gorton & Rouwenhorst (2006) show commodity futures have
  positive risk premium, negative stock correlation, and inflation protection.
- Testing both allows the data to reveal which real-asset sub-class adds more
  value in the 2000-2025 period.

Academic basis:
- Swensen (2000 / 2009) "Pioneering Portfolio Management": diversify across
  SOURCES of return, not just asset names; institutions that confine themselves
  to mainstream stocks and bonds leave enormous risk-adjusted returns on the table.
- Ilmanen (2011) "Expected Returns" Ch. 1-3: equity, bonds, real assets, and
  inflation hedges each represent distinct economic exposures.
- Erb & Harvey (2013) JFE: gold and commodity futures each have risk premia
  that are distinct from equity and bond premia.
- Brounen & De Koning (2012): real estate (REITs) has a risk premium distinct
  from equity; correlation with stocks and bonds is below 0.60 over long periods.
- Faber (2007): SMA trend timing eliminates most bear-market losses from each
  individual asset class without sacrificing long-term returns.

Tunable parameters (max 2): sma_window, use_dbc.
"""
import numpy as np
import pandas as pd

from strategies import vol_target as vt
from data.loader import load_ohlcv

EQUITY_WEIGHT = 0.25    # SPY slot
BOND_WEIGHT   = 0.25    # IEF slot
GOLD_WEIGHT   = 0.25    # GLD slot
REAL_WEIGHT   = 0.25    # VNQ or DBC slot

DEFAULTS = {"sma_window": 200, "use_dbc": False}


def multi_signals(close: pd.Series,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  real_asset: pd.Series | None = None,
                  sma_window: int = 200,
                  use_dbc: bool = False) -> pd.DataFrame:
    """Weight schedule for the Swensen 4-asset allocation.

    Args:
        close       : SPY daily adjusted close.
        ief         : IEF daily close (loaded if None).
        gld         : GLD daily close (loaded if None).
        real_asset  : 4th asset close -- VNQ (default) or DBC (if use_dbc).
                      Loaded from cache if None.
        sma_window  : SMA lookback in trading days for ALL 4 trend gates.
        use_dbc     : If True, 4th slot is DBC (commodities); if False, VNQ.

    Returns:
        Weight DataFrame with columns ['SPY', 'IEF', 'GLD', real_ticker].
        Each asset: 0.25 when above SMA(sma_window), 0 otherwise.
        Row sums in [0, 1.0]. No-lookahead via shift(1) on all gates.
    """
    real_ticker = "DBC" if use_dbc else "VNQ"

    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]
    if real_asset is None:
        real_asset = load_ohlcv(real_ticker)["Close"]

    spy_a   = close.copy()
    ief_a   = ief.reindex(close.index, method="ffill")
    gld_a   = gld.reindex(close.index, method="ffill")
    real_a  = real_asset.reindex(close.index, method="ffill")

    def _sma_gate(series: pd.Series, window: int) -> pd.Series:
        sma = series.rolling(window).mean()
        gate = (series > sma).astype(float).where(sma.notna(), 0.0)
        return gate.shift(1).fillna(0.0)

    spy_gate  = _sma_gate(spy_a, sma_window)
    ief_gate  = _sma_gate(ief_a, sma_window)
    gld_gate  = _sma_gate(gld_a, sma_window)
    real_gate = _sma_gate(real_a, sma_window)

    spy_w  = EQUITY_WEIGHT * spy_gate
    ief_w  = BOND_WEIGHT   * ief_gate
    gld_w  = GOLD_WEIGHT   * gld_gate
    real_w = REAL_WEIGHT   * real_gate

    return pd.DataFrame(
        {"SPY": spy_w, "IEF": ief_w, "GLD": gld_w, real_ticker: real_w},
        index=close.index,
    )
