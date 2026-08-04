"""Kelly-Sized CRQS (E43) — session 29 (2026-08-04).

Tests whether varying the vol_target parameter in CRQS, interpreted as
different implied Kelly fractions, produces superior geometric growth.

Background (Ed Thorp / CashMoney connection):
  CRQS's vol-target rule (exposure = min(1, vol_target / σ)) is equivalent
  to betting at a Kelly fraction given by:
      k_frac = vol_target × Sharpe_CRQS / 1  (when exposure hits 1.0)

  At vol_target=0.18 and CRQS Sharpe=0.960:
      k_equiv = 0.18 × 0.960 = 0.173  →  ~17.3% of full Kelly

  Full Kelly for CRQS = 0.960 / 0.107 ≈ 8.97×; this is far above the
  no-leverage cap of 1.0, so we are already well below full Kelly.

  Since full Kelly >> 1.0, reducing vol_target BELOW 0.18 pulls the
  exposure below 1.0 during moderate-vol regimes and is theoretically
  sub-optimal for long-run geometric growth. However, the literature
  (Haghani & Dewey 2016 "Rational Decision-Making") demonstrates that
  practitioners routinely use half-Kelly or lower due to:
    (a) Parameter estimation error (true Sharpe < observed)
    (b) Fat tails inflate observed damage beyond log-normal prediction
    (c) Human loss aversion reduces tolerance for large drawdowns

  This experiment tests vol_target ∈ {0.09, 0.12, 0.15, 0.18, 0.21, 0.24}
  on the best CRQS config (eps=0.00, sd=0.75, ct=0.00) to find the
  vol_target that maximises risk-adjusted performance.

References
----------
Thorp, E.O. (2008). The Kelly Criterion. Handbook of Asset and Liability Mgmt.
Haghani, V. & Dewey, R. (2016). Rational Decision-Making Under Uncertainty.
  SSRN 2856963.
MacLean, Thorp & Ziemba (2011). The Kelly Capital Growth Investment Criterion.
"""
from strategies.crqs import multi_signals as crqs_multi_signals


BEST_CRQS_PARAMS = {
    "eps_threshold":  0.00,
    "scale_down":     0.75,
    "corr_threshold": 0.00,
    "corr_lb":        63,
}

VOL_TARGET_GRID = [0.09, 0.12, 0.15, 0.18, 0.21, 0.24]


def multi_signals(close, shiller, ief=None, gld=None,
                  vol_target: float = 0.18, lookback: int = 20, **kwargs):
    """CRQS weights with a parametric vol_target (Kelly fraction proxy).

    Delegates to crqs.multi_signals with the best CRQS params fixed and
    vol_target as the only free parameter.

    Args:
        close      : SPY daily close.
        shiller    : Shiller monthly DataFrame.
        ief        : IEF close (loaded if None).
        gld        : GLD close (loaded if None).
        vol_target : Annualised volatility ceiling for the equity sleeve.
        lookback   : Vol estimate lookback days (keep at 20 per best CRQS).
    """
    return crqs_multi_signals(
        close, shiller, ief=ief, gld=gld,
        target_vol=vol_target,
        lookback=lookback,
        **BEST_CRQS_PARAMS,
    )
