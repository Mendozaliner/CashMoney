"""Tactical bond cash sleeve on v2 champion (session 22, E33).

When v2's equity trend signal is OFF (SPY below SMA200+band), the strategy is
holding cash. This module replaces that idle cash with IEF (7-10y Treasuries)
whenever IEF itself is above its own SMA200 trend gate. The equity signal is
UNCHANGED — only the cash sleeve management is enhanced.

Philosophy:
- In equity bear markets, Treasuries typically rally (flight to quality). When
  v2 is in cash during a bear market, holding bond ETFs can compound the
  outperformance advantage.
- A secondary trend gate on IEF (IEF > IEF_SMA200) protects against holding
  bonds in rising-rate environments (e.g., 2022: IEF fell 18% while v2 was
  also in cash from the equity bear market).
- Result: hold IEF only when BOTH the equity trend is off AND bonds are
  themselves in an uptrend.

Academic basis:
- Faber (2007) SSRN 962461: SMA trend timing works on bonds; entering only
  when price > 10-month SMA improves risk-adjusted returns.
- Asvanunt & Richardson (2017): bond trend following is profitable across
  countries and time periods.
- Hurst, Ooi, Pedersen (2017): trend following works across all asset classes.
- E20 CTA (session 12): multi-asset trend (SPY/IEF/GLD) achieved mean WF
  Sharpe 1.099 (best ever) and worst DD -6.19% — but failed the diff-CI vs
  SPY because it underperformed in the 2020-2025 equity bull market. E33 avoids
  that drag: the equity sleeve is always v2 (no CTA drag during equity bull
  markets); IEF is only used as a CASH SUBSTITUTE, not competing with equities.

Key distinctions from prior experiments:
- E30 (CLOSED): reduced equity exposure when bonds beat equities. E33 never
  reduces equity exposure — it changes the CASH RETURN only.
- E20 CTA (CLOSED): actively allocated between SPY, IEF, GLD based on trend.
  E33 only touches the cash sleeve while the equity signal runs unchanged.

Returns a multi-asset weight DataFrame (SPY + IEF) for use with multi_engine.

Tunable parameters: ief_window (IEF SMA length), cash_ief_frac (fraction
of available cash to place in IEF when conditions are met).
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

DEFAULTS = {"ief_window": 200, "cash_ief_frac": 1.0}


def multi_signals(close: pd.Series,
                  ief: pd.Series | None = None,
                  ief_window: int = 200,
                  cash_ief_frac: float = 1.0,
                  target_vol: float = 0.18,
                  lookback: int = 20) -> pd.DataFrame:
    """Weight schedule for v2 (SPY sleeve) + tactical bond cash (IEF sleeve).

    Returns a DataFrame with columns ['SPY', 'IEF'] where:
      SPY weight = v2 signal (unchanged)
      IEF weight = (1 - v2_signal) * cash_ief_frac * ief_trend_gate

    Row sums ≤ 1.0; residual cash earns the T-bill rate via multi_engine.

    Args:
        close          : SPY daily adjusted close.
        ief            : IEF daily adjusted close (loaded if None).
        ief_window     : IEF SMA window for bond trend gate (200 = SMA200).
        cash_ief_frac  : Fraction of cash sleeve to deploy into IEF (1.0 = all).
        target_vol     : V2 annualized vol target (fixed at champion 0.18).
        lookback       : V2 realized-vol lookback days (fixed at champion 20).
    """
    spy_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    if ief is None:
        ief = load_ohlcv("IEF")["Close"]

    ief_a = ief.reindex(close.index, method="ffill")

    # IEF trend gate: IEF > IEF_SMA(ief_window) → bond trend is up
    ief_sma = ief_a.rolling(ief_window).mean()
    ief_gate = (ief_a > ief_sma).astype(float).shift(1).fillna(0.0)

    # Cash available = 1 - equity exposure; allocate to IEF when gate is on
    cash_avail = (1.0 - spy_sig).clip(0.0, 1.0)
    ief_weight = cash_avail * cash_ief_frac * ief_gate

    weights = pd.DataFrame(
        {"SPY": spy_sig, "IEF": ief_weight},
        index=close.index,
    )
    return weights
