"""Faber GTAA-5 Revisited: Global Tactical Asset Allocation (session 24, E36).

Philosophy (Faber 2007, "A Quantitative Approach to Tactical Asset Allocation",
SSRN 962461): Hold five uncorrelated global asset classes in equal 20% weights
when each is above its SMA(sma_window) trend gate; otherwise hold T-bills in
that slot. The five asset classes represent the major economic return premia:

  SPY  -- US equity (growth + equity risk premium)
  EFA  -- International developed equity (geographic diversification)
  DBC  -- Broad commodity index (real asset / inflation + supply shock premium)
  VNQ  -- US real estate (inflation hedge + liquidity premium)
  IEF  -- Intermediate Treasury bonds (safe-haven / deflation hedge)

Key distinction from E10 (prior GTAA-5 test, DISCARDED on significance 2026-07-14):
  E10 was run when DBC had < 3 years of history; the ROADMAP explicitly flagged
  "revisit when DBC has more history." As of this session DBC has 19+ years
  (2006-02 → 2026-07), making the commodity-inclusive backtest valid.

Key distinction from E6 / strategies/gtaa.py (GTAA-4, watch-listed):
  E6 used SPY/IWM/IEF/GLD as the 4-asset universe. This uses Faber's ORIGINAL
  5 asset classes including international equity and commodities, replacing GLD
  with DBC (which includes gold + energy + agricultural commodities).

Academic basis:
- Faber (2007) SSRN 962461: equal-weight GTAA using 10-month SMA produces
  CAGR ~12.7%, MaxDD -9.5%, Sharpe 0.87 (1973-2005, incl. costs).
- Ilmanen (2011) "Expected Returns": each of the 5 asset classes has a
  distinct risk premium source; combining them reduces correlation.
- Gorton & Rouwenhorst (2006) FAJ: commodity futures provide positive risk
  premium, negative correlation with stocks and bonds, inflation hedge.
- Case & Shiller (1994) + Brounen & De Koning (2012): real estate returns
  have low correlation with bonds and are a genuine portfolio diversifier.

Why this can differ from v2 (SMA200 + vol-target on SPY):
  v2 is a single-asset trend strategy. GTAA-5 distributes exposure across 5
  DIFFERENT economic regimes simultaneously. In bull equity markets, only the
  SPY and EFA slots are fully active -- the commodity and real-estate slots may
  be partially or fully in cash. In stagflation (1970s-analog), DBC and VNQ
  trend ON while SPY trends OFF. The portfolio is never all-in or all-out; the
  five independent gates provide structural diversification of regime risk.

Tunable parameters (max 2): sma_window, band.
"""
import numpy as np
import pandas as pd

from data.loader import load_ohlcv

UNIVERSE = ["SPY", "EFA", "DBC", "VNQ", "IEF"]
DEFAULTS = {"sma_window": 200, "band": 0.03}
SLOT_WEIGHT = 1.0 / len(UNIVERSE)   # 0.20 per asset


def multi_signals(price_panel: pd.DataFrame | None = None,
                  sma_window: int = 200,
                  band: float = 0.03) -> pd.DataFrame:
    """Weight schedule for Faber GTAA-5.

    Args:
        price_panel : Wide Close DataFrame (date x ticker) containing at least
                      the UNIVERSE tickers. Any missing tickers are loaded from
                      the OHLCV cache and joined. Assets missing entirely are
                      given a 0 weight (T-bills earn the residual via rf_daily).
        sma_window  : SMA lookback in trading days (default 200 ≈ 10 months).
        band        : Hysteresis band: enter if close > SMA×(1+band); exit
                      below SMA×(1-band). Set 0 for pure SMA crossover.

    Returns:
        Weight DataFrame (date x ticker) with row sums <= 1.0.
        No-lookahead: SMA gate signal computed at bar-t, shift(1) applied so
        the portfolio change executes at bar t+1.
    """
    # Build panel from cache if not provided
    if price_panel is None:
        cols = {}
        for t in UNIVERSE:
            try:
                cols[t] = load_ohlcv(t)["Close"]
            except FileNotFoundError:
                pass
        price_panel = pd.DataFrame(cols).sort_index()

    idx = price_panel.index
    weights = pd.DataFrame(0.0, index=idx, columns=UNIVERSE)

    for ticker in UNIVERSE:
        if ticker not in price_panel.columns:
            continue
        close = price_panel[ticker].copy().ffill()
        sma = close.rolling(sma_window).mean()

        # Hysteresis: need close > SMA*(1+band) to enter; stay out until
        # close > SMA*(1+band) again if below SMA*(1-band).
        # Simple implementation: compute raw gate, shift for no-lookahead.
        if band > 0:
            gate = pd.Series(np.nan, index=idx)
            entered = False
            sma_vals = sma.values
            close_vals = close.values
            for i in range(len(idx)):
                if np.isnan(sma_vals[i]):
                    gate.iloc[i] = 0.0
                    continue
                if not entered:
                    if close_vals[i] > sma_vals[i] * (1 + band):
                        entered = True
                        gate.iloc[i] = 1.0
                    else:
                        gate.iloc[i] = 0.0
                else:
                    if close_vals[i] < sma_vals[i] * (1 - band):
                        entered = False
                        gate.iloc[i] = 0.0
                    else:
                        gate.iloc[i] = 1.0
        else:
            gate = (close > sma).astype(float).where(sma.notna(), 0.0)

        weights[ticker] = SLOT_WEIGHT * gate.shift(1).fillna(0.0)

    return weights.clip(0.0, 1.0)
