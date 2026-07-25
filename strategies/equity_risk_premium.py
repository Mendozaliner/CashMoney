"""Equity Risk Premium (ERP) carry signal as v2 overlay (E32).

The ERP is the expected return of equities ABOVE the risk-free rate. The
"Fed Model" (Yardeni 1999, also Lander, Orphanides & Douvogiannis 1997)
equates the equity earnings yield (1/CAPE) to the bond yield. A positive
ERP (earnings yield > risk-free rate) means equities offer carry vs. cash;
a negative ERP means equities are expensive relative to the risk-free return.

This is philosophically distinct from E31 (CAPE absolute-level tilt):
- E31 fires when CAPE is historically high in absolute terms.
- E32 fires when equities are expensive RELATIVE TO BONDS (rate-adjusted).

In the 1960s, CAPE was moderate (~18) but T-bill rates were high (~5%), so
ERP was negative. In 1999, CAPE was extreme AND rates were moderate, so both
E31 and E32 fire. In 2022, rising rates made ERP negative even at moderate
CAPE, which both E31/E32 would capture. The two signals are related but not
identical: r(ERP, CAPE_pct) < 1 because rates vary independently.

Research basis:
- Yardeni (1999): "Fed Model" — earnings yield vs 10y Treasury.
- Asness (2003) J.Portfolio Mgmt: "Fight the Fed Model" — criticizes it
  but acknowledges it has some cross-sectional predictive power.
- Siegel (2016): earnings yield is the most reliable long-run equity predictor.
- AQR (Ilmanen 2011) "Expected Returns": Carry = earnings yield vs. cash.
- Fama & French (1988): dividend yields predict returns; earnings yield
  is the more robust version.
- Arnott & Bernstein (2002): "What Risk Premium is Normal?" — ERP has been
  ~0% in recent decades, challenging Buy-and-Hold.

Skeptical prior:
- The "Fed Model" is theoretically questionable (nominal yield vs. real P/E).
- Earnings yield only predicts at decade+ horizons.
- In the 2020s, ERP turned briefly negative when rates rose; equities still
  did well, suggesting the signal is at best a mild long-run anchor.
- Implementation uses T-bill (^IRX) not 10y yield (not in pipeline), which
  may not reflect the duration risk premium correctly.

No lookahead contract:
- CAPE shifted 1 month for publication lag (same as cape_tilt.py).
- IRX is a daily observable; no shift needed.
"""

import pandas as pd
import numpy as np

from strategies import vol_target
from data import loader

TRADING_DAYS = 252


def signals(
    close: pd.Series,
    irx: pd.Series,
    target_vol: float = 0.18,
    lookback: int = 20,
    tilt_lo: float = 0.70,
    min_erp: float = 0.0,
) -> pd.Series:
    """Return fractional exposure in [0, 1] with ERP carry overlay on v2.

    Parameters
    ----------
    irx : pd.Series
        Daily ^IRX (3-month T-bill annualized rate, as a percentage like 4.5).
        Reindex to close.index before passing.
    tilt_lo : float
        Exposure multiplier when earnings_yield < T-bill rate (i.e. equities
        offer no carry advantage over cash). Default 0.70.
    min_erp : float
        Minimum ERP threshold (in decimal: 0.0 = breakeven, 0.02 = 2% spread
        required before equities are 'cheap'). Default 0.0.
    """
    base = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    try:
        shiller = loader.load_shiller()
    except FileNotFoundError:
        return base

    if "CAPE" not in shiller.columns:
        return base

    cape = shiller["CAPE"].dropna()
    if len(cape) < 120:
        return base

    # Earnings yield = 1/CAPE, shifted 1 month for publication lag
    earnings_yield = (1.0 / cape.shift(1)).dropna()

    # Forward-fill to daily
    ey_daily = earnings_yield.reindex(close.index, method="ffill")

    # T-bill rate converted to decimal (^IRX reports as percent)
    rf_daily = irx.reindex(close.index).ffill().fillna(0.0) / 100.0

    # ERP = earnings yield - risk-free rate
    erp = ey_daily - rf_daily

    # Scale: full v2 when ERP >= min_erp (equities have carry advantage)
    #        tilt_lo  when ERP <  min_erp (equities expensive vs. cash)
    mult = pd.Series(1.0, index=close.index)
    mult[erp < min_erp] = tilt_lo

    return (base * mult).clip(0.0, 1.0)
