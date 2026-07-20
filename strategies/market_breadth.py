"""Market breadth trend signal (Session 13 / E23).

Philosophy: Norman Fosback "Stock Market Logic" (1976), Martin Zweig (1986).
The health of the overall market is reflected in the BREADTH of the rally:
when most sectors are trending above their long-run averages, the market is in
a confirmed bull regime. When breadth deteriorates, risk-off signals are more
reliable than waiting for the index itself to break down.

Signal construction:
  1. Count the fraction of N sector ETFs trading above their SMA200.
  2. Apply hysteresis (Zweig-style): breadth >= upper_band -> gate ON (1.0),
     breadth <= lower_band -> gate OFF (0.0), else hold prior state.
  3. Multiply by vol-targeted SPY exposure (same vol-target as champion v2).

Academic basis:
- Fosback (1976) "Stock Market Logic" -- advance/decline breadth predicts
  market direction over 1-6 month horizons.
- Zweig (1986) "Winning on Wall Street" -- market breadth momentum rule;
  breadth thrust signals as timing entry.
- Lo & Mackinlay (1988) JFE -- cross-sectional momentum is distinct from
  index-level momentum; breadth captures it.

Constraints: uses only the 9 original SPDR sector ETFs (XLK/XLF/XLE/XLV/XLY/
XLP/XLI/XLU/XLB) to preserve full 2000->present history across all WF folds.
XLC (2018) and XLRE (2015) are excluded to prevent data-length snooping.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB']


def breadth_score(sector_panel: pd.DataFrame,
                  sma_window: int = 200) -> pd.Series:
    """Fraction of sectors in sector_panel currently above their SMA(sma_window).
    NaN values (e.g. warmup) are treated as 'below SMA' (conservative)."""
    above = pd.DataFrame(index=sector_panel.index, columns=sector_panel.columns,
                         dtype=float)
    for col in sector_panel.columns:
        sma = sector_panel[col].rolling(sma_window, min_periods=sma_window).mean()
        above[col] = (sector_panel[col] > sma).astype(float)
    return above.mean(axis=1).fillna(0.0)


def signals(close_spy: pd.Series,
            sector_panel: pd.DataFrame,
            sma_window: int = 200,
            upper_band: float = 0.6,
            lower_band: float = 0.4,
            vol_target: float = 0.18,
            vol_window: int = 20) -> pd.Series:
    """Breadth-gated, vol-targeted SPY exposure signal.

    Args:
        close_spy   : SPY adjusted close price series.
        sector_panel: Wide DataFrame of sector ETF closes (date x ticker).
        sma_window  : SMA lookback for the breadth gate (bars).
        upper_band  : Breadth fraction above which the gate turns ON.
        lower_band  : Breadth fraction below which the gate turns OFF.
        vol_target  : Annualized vol target for the SPY sleeve.
        vol_window  : Realized-vol rolling window (bars).

    Returns:
        Exposure in [0, 1], same DatetimeIndex as close_spy.
    """
    # 1. Breadth score (fraction of sectors above SMA200)
    bd = breadth_score(sector_panel.reindex(close_spy.index), sma_window)

    # 2. Hysteresis gate
    raw = pd.Series(np.nan, index=close_spy.index, dtype=float)
    raw[bd >= upper_band] = 1.0
    raw[bd <= lower_band] = 0.0
    gate = raw.ffill().fillna(0.0)

    # 3. Vol-targeting on SPY (same as champion v2 but gated by breadth)
    rv = close_spy.pct_change().rolling(vol_window).std() * np.sqrt(TRADING_DAYS)
    scale = (vol_target / rv).clip(upper=1.0).fillna(1.0)

    return (gate * scale).clip(0.0, 1.0).fillna(0.0)
