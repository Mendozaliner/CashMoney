"""Defensive Asset Allocation (DAA) with Canary Universe (E27).

Philosophy: Keller & Keuning (2018). The key innovation over VAA (E25):
a SEPARATE canary universe (EEM, AGG) acts as an economic health barometer,
INDEPENDENT from the tradeable offensive/defensive universe. This separates
two concerns:
  1. "Is the market sick?" → canary universe signals recession risk
  2. "What should I buy?" → offensive/defensive universe, scored by momentum

The canary assets (EEM = emerging markets, AGG = aggregate bonds) lead
economic downturns earlier than domestic equity indices. A falling EEM
signals global risk-off; a falling AGG signals credit stress or rising rates.
Either signal individually is enough to initiate defensive rotation.

Successful philosophies incorporated:
  - Dual Momentum (Antonacci 2014): absolute momentum bar for each asset
  - VAA (Keller 2017): 13612W weighted momentum score
  - Risk Parity: equal allocation between offense and defense when 1 canary negative
  - Permanent Portfolio (Browne): defensive assets always in pool

Unsuccessful philosophies learned from:
  - VAA (E25): failed because breadth_prot=0.30 with n=3 is still too slow —
    all 3 offensive assets decline before defense triggers. DAA fixes this by
    watching a SEPARATE canary universe, so defense triggers independently.
  - Dual Momentum (E3/E7): TLT harbor was too rigid in 2022. DAA fixes by
    competitive defensive selection (best of SHY/IEF/TLT/GLD by 13612W score).
  - GTAA (E6): too correlated to v2 (0.721) because it uses same assets.
    DAA uses EEM/AGG as canary — assets the v2 champion never trades.

Allocation rule (monthly rebalance at month-end):
  Let n_neg = # canary assets with 13612W score <= 0
  Let def_frac = min(1.0, n_neg * canary_sensitivity)
  off_frac = 1.0 - def_frac
  → Allocate off_frac to highest-scored offensive asset
  → Allocate def_frac to highest-scored defensive asset
  (canary_sensitivity=0.5: graded; =1.0: any negative → fully defensive)

Parameters (max 2):
  canary_sensitivity : float — defensive fraction PER negative canary.
                       0.5 = 50% defensive per negative canary (original paper)
                       1.0 = any negative canary → 100% defensive (strictest)
  offensive_n        : int — # offensive assets: 3=(SPY,QQQ,IWM), 4=adds GLD

Reference: Keller, W.J. & Keuning, J.W. (2018). "Breadth Momentum and
Vigilant Asset Allocation (DAA update)." SSRN 3002624v2.
"""
import numpy as np
import pandas as pd

CANARY_ASSETS   = ["EEM", "AGG"]
OFFENSIVE_POOL  = ["SPY", "QQQ", "IWM", "GLD"]
DEFENSIVE_POOL  = ["SHY", "IEF", "TLT", "GLD"]

_LB_DAYS    = [21, 63, 126, 252]
_LB_WEIGHTS = [12,  4,   2,   1]


def _compute_scores(price_panel: pd.DataFrame, assets: list) -> pd.DataFrame:
    """Vectorized 13612W momentum score (causal: uses only past prices)."""
    avail = [a for a in assets if a in price_panel.columns]
    if not avail:
        return pd.DataFrame(index=price_panel.index)
    px = price_panel[avail]
    score = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for lb, w in zip(_LB_DAYS, _LB_WEIGHTS):
        ret = px / px.shift(lb) - 1.0
        score = score + w * ret
    return score


def multi_signals(price_panel: pd.DataFrame,
                  canary_sensitivity: float = 0.5,
                  offensive_n: int = 4) -> pd.DataFrame:
    """Weight DataFrame (date x ticker). Monthly rebalance on last trading day.

    canary_sensitivity : Defensive fraction per negative canary [0.5, 1.0].
                         0.5 → 1 neg canary = 50% defensive; 2 = 100%.
                         1.0 → any negative canary = 100% defensive.
    offensive_n        : Number of offensive assets from OFFENSIVE_POOL [3, 4].
    """
    canary    = [c for c in CANARY_ASSETS if c in price_panel.columns]
    off_pool  = [a for a in OFFENSIVE_POOL[:offensive_n] if a in price_panel.columns]
    def_pool  = [a for a in DEFENSIVE_POOL if a in price_panel.columns]

    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)

    if not canary or not off_pool or not def_pool:
        return weights

    all_score_assets = list(dict.fromkeys(canary + off_pool + def_pool))
    score = _compute_scores(price_panel, all_score_assets)

    month_end_dates = (pd.Series(True, index=price_panel.index)
                       .groupby([price_panel.index.year,
                                 price_panel.index.month])
                       .tail(1).index)

    signals_me = pd.DataFrame(0.0, index=month_end_dates,
                              columns=price_panel.columns)

    for date in month_end_dates:
        iloc_pos = price_panel.index.get_loc(date)
        if iloc_pos < 252:
            continue

        s = score.loc[date]

        n_neg = sum(
            1 for c in canary
            if c in s.index and not np.isnan(float(s[c])) and float(s[c]) <= 0.0
        )

        def_frac = min(1.0, n_neg * float(canary_sensitivity))
        off_frac = 1.0 - def_frac

        if off_frac > 0.0:
            off_scores = {
                a: float(s[a]) for a in off_pool
                if a in s.index and not np.isnan(float(s[a]))
            }
            if off_scores:
                best_off = max(off_scores, key=off_scores.get)
                if best_off in signals_me.columns:
                    signals_me.loc[date, best_off] = (
                        signals_me.loc[date, best_off] + off_frac
                    )

        if def_frac > 0.0:
            def_scores = {
                a: float(s[a]) for a in def_pool
                if a in s.index and not np.isnan(float(s[a]))
            }
            if def_scores:
                best_def = max(def_scores, key=def_scores.get)
                if best_def in signals_me.columns:
                    signals_me.loc[date, best_def] = (
                        signals_me.loc[date, best_def] + def_frac
                    )

    daily = signals_me.reindex(price_panel.index).ffill().fillna(0.0)
    weights.update(daily)
    return weights.clip(0.0, 1.0)
