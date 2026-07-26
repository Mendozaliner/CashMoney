"""Yield-curve regime overlay on v2 champion (session 22, E32).

Uses the relative momentum of IEF (7-10y Treasuries) vs SHY (1-3y Treasuries)
as a proxy for yield-curve slope health. When the long end underperforms the
short end over the lookback window, the yield curve is flattening or inverting,
which historically precedes recessions and equity drawdowns. In such regimes,
v2 equity exposure is scaled down by `invert_scale`.

Academic basis:
- Harvey (1988, 1989): inverted 3m-10y yield curve is the best single
  predictor of US recessions, with a 4-8 quarter lead time.
- Estrella & Mishkin (1998) Rev Econ Stat: 3m-10y spread dominates in
  out-of-sample recession forecasting over 1-4 quarter horizons.
- Ang, Piazzesi, Wei (2006) JFE: yield curve factors (level, slope, curvature)
  carry macroeconomic information beyond what the short rate conveys.
- Fama & French (1989): yield curve slope forecasts equity returns at
  business-cycle frequency (12-18 month horizons).

Key distinction from E30 (CLOSED):
- E30 compared bonds vs EQUITIES (IEF vs SPY). That failed (corr_v2=0.974)
  because when IEF outperforms SPY, v2's SMA200 gate had already signaled cash.
- This strategy compares SHORT bonds vs LONG bonds (SHY vs IEF), measuring the
  yield-curve shape independently of equity performance. This is orthogonal to
  the SMA200 gate: the curve can invert BEFORE equities decline (as in 2019),
  giving an earlier warning that the gate cannot see.

Skeptical prior: yield curve signal has a 4-8 quarter lead time; in the
2022-2024 inversion the curve was inverted for 22 months while equities rallied
(2023-2024). That would likely hurt OOS performance in fold-3. This does NOT
mean the signal is wrong about recession risk — just that the lead time is too
long for a 1-year trading horizon. Expect FAIL or watch-list.

Tunable parameters: lookback, invert_scale.
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

DEFAULTS = {"lookback": 252, "invert_scale": 0.50}


def signals(close: pd.Series,
            ief: pd.Series | None = None,
            shy: pd.Series | None = None,
            lookback: int = 252,
            invert_scale: float = 0.50,
            target_vol: float = 0.18,
            vol_lookback: int = 20) -> pd.Series:
    """Return exposure signal with yield-curve flattening reduction.

    When 12-month IEF momentum lags SHY momentum (curve flattening/inverting),
    v2 exposure is multiplied by `invert_scale`. When the curve is normal
    (IEF >= SHY over the lookback), full v2 exposure is maintained.

    Args:
        close        : SPY daily adjusted close.
        ief          : IEF daily adjusted close (loaded if None).
        shy          : SHY daily adjusted close (loaded if None).
        lookback     : Momentum lookback in trading days (252 ≈ 12 months).
        invert_scale : Exposure multiplier when curve is inverted (0.50 = 50%).
        target_vol   : V2 annualized vol target (fixed at champion 0.18).
        vol_lookback : V2 realized-vol lookback days (fixed at champion 20).
    """
    base = vol_target.signals(close, target_vol=target_vol, lookback=vol_lookback)

    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if shy is None:
        shy = load_ohlcv("SHY")["Close"]

    ief_a = ief.reindex(close.index, method="ffill")
    shy_a = shy.reindex(close.index, method="ffill")

    # N-day return momentum for each bond ETF
    ief_mom = ief_a.pct_change(lookback)
    shy_mom = shy_a.pct_change(lookback)

    # Normal curve: IEF (long end) >= SHY (short end) over the lookback
    # This means duration is being rewarded → investors expect lower rates
    # → accommodative / normal slope → risk-on
    curve_normal = (ief_mom >= shy_mom).astype(float)

    # Shift by 1 bar: signal at bar t uses only data through bar t's close;
    # the position fills at bar t+1. Using .shift(1) on top of the SHY/IEF
    # momentum (which already uses bar-t closes) ensures no lookahead.
    curve_factor = (
        (curve_normal + (1.0 - curve_normal) * invert_scale)
        .shift(1)
        .fillna(1.0)       # no data yet → assume normal curve
    )

    return (base * curve_factor).clip(0.0, 1.0)
