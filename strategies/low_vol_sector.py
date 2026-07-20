"""Low-volatility sector rotation (Session 13 / E24).

Philosophy: Baker & Haugen (2012) "Low Risk Stocks Outperform Within All
Observable Markets of the World." The low-volatility anomaly shows that
lower-realized-volatility assets produce HIGHER risk-adjusted returns over
time -- the opposite of what traditional CAPM predicts.

Applied here to sector ETFs: each month, rank the 9 original SPDR sector
ETFs by their 20-day realized volatility, hold the top_n lowest-vol sectors
in equal weight. An SMA200 trend gate (optional) prevents holding sectors in
technical downtrends, addressing the anomaly's known failure in bear markets
(sectors in downtrends can stay low-vol for the wrong reasons).

Academic basis:
- Haugen & Heins (1972): risk-return trade-off often inverted in equities.
- Baker, Bradley & Wurgler (2011) FAJ: institutionalbehavioral constraints
  explain persistence of the low-vol anomaly.
- Frazzini & Pedersen (2014) JFE "Betting Against Beta": low-beta assets
  earn higher risk-adjusted returns than high-beta assets (AQR empirical).
- Blitz & van Vliet (2007) JPM: low-volatility sector rotation outperforms
  within equity markets.

Constraints: uses 9 original SPDR sector ETFs with full 2000+ history.
Monthly rebalancing (end of month), held until next rebalance.
Long-only, no leverage (G1). Sector weight cap: 1/top_n each (G4 per sector).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB']


def multi_signals(sector_panel: pd.DataFrame,
                  top_n: int = 4,
                  vol_window: int = 20,
                  sma_window: int = 200,
                  use_trend_gate: bool = True) -> pd.DataFrame:
    """Monthly low-vol sector rotation weights.

    Args:
        sector_panel    : Wide DataFrame of sector ETF closes (date x ticker).
        top_n           : Number of lowest-vol sectors to hold each month.
        vol_window      : Realized-vol lookback (bars).
        sma_window      : SMA lookback for trend gate (bars).
        use_trend_gate  : If True, exclude sectors below their SMA(sma_window).

    Returns:
        Weight DataFrame (date x ticker), row sums <= 1.0.
        Rebalances at end of month; daily rows forward-filled.
    """
    cols = [c for c in SECTOR_ETFS if c in sector_panel.columns]
    panel = sector_panel[cols].copy()

    # Realized vol (annualized)
    rv = panel.pct_change().rolling(vol_window, min_periods=vol_window).std() * np.sqrt(TRADING_DAYS)

    # Trend gate: sectors above SMA200 are eligible
    sma = panel.rolling(sma_window, min_periods=sma_window).mean()
    in_uptrend = (panel > sma)

    # Daily "desired" weights: eligible_rv = rv, pushed to inf if not eligible
    if use_trend_gate:
        eligible_rv = rv.where(in_uptrend, other=np.inf)
    else:
        eligible_rv = rv.copy()

    # Rank ascending (lowest vol = lowest rank = selected first)
    ranks = eligible_rv.rank(axis=1, method='first', ascending=True, na_option='bottom')
    in_portfolio = (ranks <= top_n) & eligible_rv.lt(np.inf)

    n_held = in_portfolio.sum(axis=1).replace(0, np.nan)
    daily_weights = in_portfolio.astype(float).div(n_held, axis=0).fillna(0.0)

    # Resample to end-of-month (take last available daily weight each month)
    monthly_w = daily_weights.resample('ME').last()

    # Reindex to daily calendar and forward-fill within month
    weights = monthly_w.reindex(panel.index, method='ffill').fillna(0.0)

    return weights
