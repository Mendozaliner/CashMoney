"""Faber GTAA (Global Tactical Asset Allocation) adapted to the cache universe.

Philosophy: diversified trend-following. Each asset class occupies a FIXED
slot (1/N of capital) and is held only while trading above its own long-term
moving average at month-end; a slot whose asset is below trend sits in T-bills.
Unlike Dual Momentum (E3, discarded s5), there is NO forced safe-haven asset:
in a 2022-style joint stock/bond selloff every slot independently de-risks to
cash rather than parking in crashing duration.

Rules (Faber 2007/2013):
  1. At each month-end, for each asset: include iff Close > SMA(window)*(1+band).
  2. Included assets get weight 1/N_assets (fixed slot, NOT renormalized);
     excluded slots earn the T-bill rate (handled by multi_engine cash sleeve).
  3. Weights held constant intra-month (daily rows forward-filled).

Research basis:
- Faber, M. (2007, rev. 2013). "A Quantitative Approach to Tactical Asset
  Allocation." Journal of Wealth Management / SSRN 962461. 10-month SMA gate
  across 5 asset classes: equity-like CAGR, drawdown cut roughly in half.
- Real-time trackers (AllocateSmartly, PortfolioDB) document material
  out-of-sample decay vs the paper — hence the strict DSR/CI bar here.
- Skeptical prior: our universe (SPY/IWM/IEF/GLD) is narrower than Faber's 5
  and GLD truncates fold 1 to post-2005 (misses the dot-com bust).

Parameters (max 2): window (SMA days), band (fractional buffer on the SMA).
"""
import pandas as pd

DEFAULT_ASSETS = ["SPY", "IWM", "IEF", "GLD"]
DEFAULTS = {"window": 200, "band": 0.0}


def multi_signals(price_panel: pd.DataFrame, window: int = 200,
                  band: float = 0.0, assets=None) -> pd.DataFrame:
    """Weight DataFrame (date x ticker): 1/N slots gated on each asset's SMA.

    Decisions are taken on the last trading day of each month and held for
    the following month (weights ffilled daily). Assets with insufficient
    history stay at weight 0 (their slot sits in cash) until the SMA warms up.
    """
    assets = [a for a in (assets or DEFAULT_ASSETS) if a in price_panel.columns]
    n = len(assets)
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if n == 0:
        return weights

    px = price_panel[assets]
    sma = px.rolling(window).mean()
    on = px.gt(sma * (1.0 + band)) & sma.notna()

    # Month-end decision rows, held (ffilled) through the following month
    month_end = pd.Series(True, index=px.index).groupby(
        [px.index.year, px.index.month]).tail(1).index
    on_me = on.loc[on.index.isin(month_end)]
    on_daily = on_me.reindex(px.index).ffill().fillna(False).astype(bool)

    for a in assets:
        weights.loc[on_daily[a], a] = 1.0 / n
    return weights
