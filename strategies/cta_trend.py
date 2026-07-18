"""Multi-Asset CTA-style Trend Following with vol-targeting (session 12).

Philosophy: Managed futures / CTA funds apply trend-following across multiple
uncorrelated asset classes simultaneously, capturing 'crisis alpha' during
equity bear markets when bonds or gold are trending in the opposite direction.

Rule per asset i:
    trend_i   = SMA(window)/band gate (same as champion v2)
    rv_i      = annualized 20-day realized vol
    signal_i  = trend_i * min(1, vol_target / rv_i)

Portfolio weights (two modes):
    equal_budget: weight_i = signal_i / N_assets  [row sum <= 1.0 always]
    normalized:   scale all weights so sum = min(row_sum, target_exposure)
                  [uses full target_exposure whenever any assets are trending]

Academic basis:
- Hurst, Ooi, Pedersen (2013) "A Century of Evidence on Trend-Following
  Investing", AQR -- trend works across equities, bonds, currencies, commodities
  over 100 years; diversification is the key benefit.
- Asness, Moskowitz, Pedersen (2013) JF -- time-series momentum is
  significantly positive and uncorrelated across asset classes.
- AQR (2020) -- managed futures provide crisis alpha precisely when equity
  trend-following goes flat (bonds/gold trending UP during equity crashes).

Constraints: long-only (G1, G2), no leverage (G1), whitelist only (G2).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def multi_signals(price_panel: pd.DataFrame,
                  assets: list | None = None,
                  sma_window: int = 200,
                  band: float = 0.03,
                  vol_target: float = 0.15,
                  vol_window: int = 20,
                  normalize: bool = False,
                  target_exposure: float = 1.0) -> pd.DataFrame:
    """Multi-asset vol-targeted trend signals.

    Args:
        price_panel : Wide Close DataFrame (date x ticker).
        assets      : Ordered list of tickers to trade (subset of panel cols).
                      Defaults to all columns.
        sma_window  : SMA lookback for the trend gate (bars).
        band        : Hysteresis band (fraction of SMA). Same as champion v2.
        vol_target  : Annualized vol target per asset in equal_budget mode,
                      or per unit of the combined portfolio in normalized mode.
        vol_window  : Realized-vol rolling window (bars).
        normalize   : If True, rescale weights each day so total exposure equals
                      min(raw_sum, target_exposure). If False (equal_budget),
                      each asset weight = signal / N_assets.
        target_exposure : Used only when normalize=True. Cap on total exposure.
    Returns:
        weights : DataFrame (date x assets), row sums <= target_exposure.
    """
    if assets is None:
        assets = list(price_panel.columns)

    signals = pd.DataFrame(0.0, index=price_panel.index, columns=assets)

    for asset in assets:
        close = price_panel[asset].copy()
        if close.dropna().empty:
            continue

        sma = close.rolling(sma_window).mean()
        raw = pd.Series(np.nan, index=close.index, dtype=float)
        raw[close > sma * (1 + band)] = 1.0
        raw[close < sma * (1 - band)] = 0.0
        trend = raw.ffill().fillna(0.0)

        rv = close.pct_change().rolling(vol_window).std() * np.sqrt(TRADING_DAYS)
        rv = rv.replace(0, np.nan).ffill()
        scale = (vol_target / rv).clip(upper=1.0).fillna(0.0)

        signals[asset] = (trend * scale).fillna(0.0).clip(0.0, 1.0)

    if normalize:
        row_sum = signals.sum(axis=1)
        safe_sum = row_sum.replace(0, np.nan)
        norm_factor = (target_exposure / safe_sum).clip(upper=1.0).fillna(1.0)
        weights = signals.multiply(norm_factor, axis=0)
    else:
        weights = signals / len(assets)

    return weights.fillna(0.0)
