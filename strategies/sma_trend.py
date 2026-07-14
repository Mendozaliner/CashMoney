"""Long/flat SMA trend filter on a broad equity index (SPY proxy).

Rule: long when Close > SMA(window) * (1 + band); flat ("cash", 0% yield)
when Close < SMA(window) * (1 - band); otherwise keep the previous state
(hysteresis band reduces whipsaw trades and hence cost drag).

Research basis:
- Faber (2007), "A Quantitative Approach to Tactical Asset Allocation",
  J. Wealth Mgmt. -- 10-month SMA timing achieved equity-like returns with
  bond-like drawdowns. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
- Zakamulin (2014), "The real-life performance of market timing with moving
  average and time-series momentum rules", J. Asset Mgmt 15(4) -- with
  realistic costs and out-of-sample testing, the edge is mostly in *risk
  reduction*, not raw return. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2242795
- Zakamulin (2018), "Revisiting the Profitability of Market Timing with
  Moving Averages", Int. Rev. Finance -- data-mining-bias warnings.

Tunable parameters (max 2): window, band.
"""
import numpy as np
import pandas as pd

DEFAULTS = {"window": 200, "band": 0.02}


def signals(close: pd.Series, window: int = 200, band: float = 0.02) -> pd.Series:
    sma = close.rolling(window).mean()
    raw = pd.Series(np.nan, index=close.index, dtype=float)
    raw[close > sma * (1 + band)] = 1.0
    raw[close < sma * (1 - band)] = 0.0
    return raw.ffill().fillna(0.0)
