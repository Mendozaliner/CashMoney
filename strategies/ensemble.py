"""Ensemble blending utilities (Session 13 / E22).

Combines champion v2 (SPY trend + vol target) with CTA multi-asset trend
(SPY/IEF/GLD) using a fixed-weight blend. v2 contributes better terminal
equity value; CTA contributes lower drawdown and higher Sharpe.

The corr(v2, CTA) = 0.635 was above the prior 0.50 ensemble threshold but is
below 0.70 -- a threshold the roadmap flagged as worth testing (STATE.md s12,
item #5). This file implements the blend for E22.

Blend formula (per day):
    blended[SPY] = alpha * v2_signal + (1-alpha) * cta_spy
    blended[IEF] = (1-alpha) * cta_ief
    blended[GLD] = (1-alpha) * cta_gld

Row sums are bounded by 1.0 because:
    max(v2_signal) = 1.0  and  sum(cta_weights) <= 1.0
    => max row sum = alpha*1 + (1-alpha)*1 = 1.0   (no leverage)

Academic basis:
- Markowitz (1952) JF: diversification reduces portfolio variance.
- Lo (2010): Sharpe of an ensemble of N uncorrelated strategies improves
  by sqrt(N); at corr=0.635 the theoretical Sharpe gain = 1/(1+rho) factor.
- Asness (2016) FAJ: diversification of trend-following across asset classes
  is the primary source of CTA excess returns.
"""
import pandas as pd
import numpy as np

from strategies import vol_target as vt
from strategies import cta_trend as cta


def v2_cta_signals(price_panel: pd.DataFrame,
                   alpha: float = 0.5,
                   cta_assets: list | None = None,
                   cta_vol_target: float = 0.12,
                   v2_target_vol: float = 0.18,
                   v2_lookback: int = 20,
                   sma_window: int = 200,
                   band: float = 0.03,
                   vol_window: int = 20) -> pd.DataFrame:
    """Blend v2 (SPY) and CTA (SPY/IEF/GLD) into a multi-asset weight DataFrame.

    Args:
        price_panel   : Wide Close DataFrame (date x ticker) — must include SPY
                        and all cta_assets.
        alpha         : v2 weight in the blend (0=pure CTA, 1=pure v2).
        cta_assets    : Tickers for CTA sleeve (default: ['SPY','IEF','GLD']).
        cta_vol_target: Vol target passed to the CTA signals function.
        v2_target_vol : Vol target for the v2 SPY signal.
        v2_lookback   : Realized-vol lookback for v2.
        sma_window    : SMA window shared by both strategies.
        band          : Hysteresis band for SMA trend gate.
        vol_window    : Realized-vol window for CTA.

    Returns:
        Weight DataFrame (date x ticker) with columns = union of ['SPY'] and
        cta_assets. Row sums <= 1.0.
    """
    if cta_assets is None:
        cta_assets = ['SPY', 'IEF', 'GLD']

    spy = price_panel['SPY'].copy()

    # v2 signal on SPY
    v2_sig = vt.signals(spy, target_vol=v2_target_vol, lookback=v2_lookback)

    # CTA signals on multi-asset panel
    cta_panel = price_panel.reindex(columns=cta_assets)
    cta_w = cta.multi_signals(cta_panel, assets=cta_assets,
                              sma_window=sma_window, band=band,
                              vol_target=cta_vol_target, vol_window=vol_window,
                              normalize=False)

    # Build blended weight matrix
    all_cols = list(dict.fromkeys(['SPY'] + cta_assets))
    blended = pd.DataFrame(0.0, index=price_panel.index, columns=all_cols)

    # v2 contribution: SPY only
    blended['SPY'] += alpha * v2_sig.reindex(price_panel.index).fillna(0.0)

    # CTA contribution
    for col in cta_assets:
        if col in cta_w.columns:
            blended[col] = blended.get(col, 0.0) + (
                (1 - alpha) * cta_w[col].reindex(price_panel.index).fillna(0.0)
            )

    return blended.clip(0.0, 1.0).fillna(0.0)
