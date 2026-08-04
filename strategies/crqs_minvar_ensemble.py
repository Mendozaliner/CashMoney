"""CRQS + MinVar Ensemble (E44) — session 29 (2026-08-04).

Tests whether blending the CRQS champion with the MinVar portfolio achieves
a better risk-adjusted outcome than either strategy alone, leveraging their
exceptionally low correlation (MinVar corr_v2 = 0.267, all-time project record).

Investment philosophy: Diversification across uncorrelated strategies
(Markowitz 1952; Dalio "All Weather"). A blend of two strategies with:
  - High Sharpe but correlated to SPY (CRQS: Sharpe 0.960, corr_v2 0.923)
  - Lower Sharpe but uncorrelated (MinVar: mean_wf Sharpe ~0.887, corr_v2 0.267)
can outperform either standalone on a risk-adjusted basis if the correlation
between the strategies is sufficiently low.

The correlation between CRQS and MinVar can be estimated from their
correlation to v2:
  corr(CRQS, MinVar) ≈ corr(v2, MinVar) × corr(v2, CRQS) = 0.267 × 0.923 ≈ 0.246

At blend_w=0.80 (80% CRQS, 20% MinVar):
  Expected Sharpe ≈ (0.80 × 0.960 + 0.20 × 0.887) × diversification_factor
  Diversification is strongest when correlation is lowest.

Known limitation: MinVar end$1k = $3,251 vs CRQS $12,104. Any blend drags
terminal value. The trade-off is lower drawdown for lower compound return.

References
----------
Markowitz, H. (1952). Portfolio Selection. Journal of Finance.
Dalio, R. (2011). How the Economic Machine Works. Bridgewater Associates.
Ilmanen, A. (2011). Expected Returns. Wiley. Ch. 6 — Strategy Diversification.
"""
import pandas as pd
from strategies.crqs import multi_signals as crqs_signals
from strategies.min_var import multi_signals as minvar_signals


BLEND_GRID = [0.95, 0.90, 0.80, 0.70, 0.60]

CRQS_PARAMS = {
    "eps_threshold":  0.00,
    "scale_down":     0.75,
    "corr_threshold": 0.00,
    "corr_lb":        63,
    "target_vol":     0.18,
    "lookback":       20,
}

MINVAR_PARAMS = {
    "cov_lookback": 60,
    "sma_gate":     False,
}


def multi_signals(price_panel: pd.DataFrame,
                  shiller,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  blend_w: float = 0.80) -> pd.DataFrame:
    """Blended CRQS + MinVar weight DataFrame.

    Args:
        price_panel : Wide close-price DataFrame (date × ticker).
        shiller     : Shiller monthly DataFrame.
        ief         : IEF close (optional, loaded internally by crqs if None).
        gld         : GLD close (optional, loaded internally by crqs if None).
        blend_w     : Weight on CRQS (0-1); remainder goes to MinVar.
                      blend_w=1.0 → pure CRQS; blend_w=0.0 → pure MinVar.

    Returns:
        DataFrame of blended weights (same schema as crqs.multi_signals output).
    """
    spy_close = price_panel["SPY"]

    crqs_w = crqs_signals(spy_close, shiller, ief=ief, gld=gld, **CRQS_PARAMS)
    crqs_w = crqs_w.reindex(price_panel.index).fillna(0.0)

    mv_w = minvar_signals(price_panel, **MINVAR_PARAMS)
    mv_w = mv_w[["SPY", "IEF", "GLD"]].reindex(price_panel.index).fillna(0.0)

    blended = blend_w * crqs_w + (1.0 - blend_w) * mv_w

    row_sums = blended.sum(axis=1)
    over = row_sums > 1.0
    if over.any():
        blended.loc[over] = blended.loc[over].div(row_sums[over], axis=0)

    return blended
