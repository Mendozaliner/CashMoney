"""Vigilant Asset Allocation (VAA) - Keller & Keuning 2017.

Philosophy: absolute momentum scoring + breadth protection.
Score = 12*M1 + 4*M3 + 2*M6 + 1*M12 for each asset.
If fraction(offensive assets scoring <= 0) >= breadth_prot:
    rotate 100% into the defensive asset with the highest score.
Else:
    rotate 100% into the offensive asset with the highest score.
Monthly rebalance at each month-end.

Key differences from GTAA (E6):
  - Uses a WEIGHTED MOMENTUM SCORE (not a binary SMA cross). Short-term
    momentum receives 3x more weight than long-term (12× for 1-month vs
    4× for 3-month), making the signal more sensitive to trend breaks.
  - BREADTH PROTECTION: even a single faltering offensive asset can
    trigger full defensive rotation (breadth_prot=0.30 for n=3 assets).
    This reflects the empirical finding that bear markets infect asset
    classes rapidly — waiting for majority failure is too slow.
  - Always holds EXACTLY ONE asset (100% concentration), not equal-weight.
    Avoids the fixed-slot drag of GTAA during uniform downtrends.

Unsuccessful philosophies captured / why they fail:
  - GTAA (E6): correlation 0.721 to v2 (near-duplicate in bull markets).
    VAA solves this by: (a) holding 100% best vs 1/4 each, and (b) using
    score-based selection rather than SMA gate.
  - Dual Momentum (E3/E7): failed because SPY/QQQ/DIA rotation whipsaws
    and the harbor (TLT or SHY) was too rigid. VAA solves this with a
    COMPETITIVE defensive selection — SHY, IEF, TLT, and GLD all compete
    on score, so 2022-style bond carnage auto-routes to GLD or SHY.
  - Sector momentum (E5/E11): momentum crash in bear markets; no trend gate.
    VAA solves this with the breadth-protection mechanism, which removes
    all equity exposure at the first sign of broad market deterioration.

Parameters (max 2):
  breadth_prot : float — fraction of offensive assets that must score <= 0
                 to trigger defensive. 0.30 = any 1 of 3 (G1 variant);
                 0.50 = majority; 0.90 = all must fail (most permissive).
  offensive_n  : int — size of offensive universe: 3=(SPY,QQQ,IWM),
                 4=(SPY,QQQ,IWM,EFA).

Reference: Keller, W.J. & Keuning, J.W. (2017). "Breadth Momentum and the
Vigilant Asset Allocation (VAA) Strategy." SSRN 3002624.
"""
import numpy as np
import pandas as pd

OFFENSIVE_POOL = ["SPY", "QQQ", "IWM", "EFA"]   # first n chosen
DEFENSIVE_POOL = ["SHY", "IEF", "TLT", "GLD"]

_LB_DAYS    = [21, 63, 126, 252]   # 1, 3, 6, 12 months in trading days
_LB_WEIGHTS = [12,  4,   2,   1]   # VAA score weights


def _compute_scores(price_panel: pd.DataFrame, assets: list) -> pd.DataFrame:
    """Vectorized VAA momentum score matrix (date × asset). Causal: uses only
    past prices at each row. NaN where history is insufficient."""
    px = price_panel[assets]
    score = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for lb, w in zip(_LB_DAYS, _LB_WEIGHTS):
        ret = px / px.shift(lb) - 1.0
        score = score + w * ret
    return score


def multi_signals(price_panel: pd.DataFrame,
                  breadth_prot: float = 0.30,
                  offensive_n: int = 3) -> pd.DataFrame:
    """Weight DataFrame (date × ticker): 100% in one asset, monthly rebalance.

    breadth_prot : Fraction of offensive assets that must score <= 0 to trigger
                   defensive rotation. E.g. 0.30 → any 1 of 3 triggers defense;
                   0.50 → 2 of 3 must fail; 0.90 → all three must fail.
    offensive_n  : Number of offensive assets to use from OFFENSIVE_POOL.
                   3 = (SPY, QQQ, IWM); 4 adds EFA.

    Returns a DataFrame of weights with the same index/columns as price_panel.
    Row sums are 0 (cash) or 1.0 (fully invested in one asset).
    """
    off_assets = [a for a in OFFENSIVE_POOL[:offensive_n]
                  if a in price_panel.columns]
    def_assets = [a for a in DEFENSIVE_POOL if a in price_panel.columns]

    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if not off_assets or not def_assets:
        return weights

    all_assets = off_assets + def_assets
    score = _compute_scores(price_panel[all_assets], all_assets)

    # Last trading day of each calendar month
    month_end_dates = (pd.Series(True, index=price_panel.index)
                       .groupby([price_panel.index.year,
                                 price_panel.index.month])
                       .tail(1).index)

    signals_me = pd.DataFrame(0.0, index=month_end_dates,
                              columns=price_panel.columns)

    for date in month_end_dates:
        iloc_pos = price_panel.index.get_loc(date)
        if iloc_pos < 252:          # require ~1 year of history to score 12-month
            continue

        s = score.loc[date]

        # Offensive assets with valid (non-NaN) scores
        off_valid = [a for a in off_assets if not np.isnan(s[a])]
        if not off_valid:
            continue

        n_neg = sum(1 for a in off_valid if s[a] <= 0.0)
        frac_neg = n_neg / len(off_valid)

        if frac_neg >= breadth_prot:
            # Breadth protection triggered → best defensive by score
            def_valid = {a: float(s[a]) for a in def_assets
                         if not np.isnan(s[a])}
            if def_valid:
                best = max(def_valid, key=def_valid.get)
                signals_me.loc[date, best] = 1.0
        else:
            # All clear → best offensive by score
            off_scores = {a: float(s[a]) for a in off_valid}
            best = max(off_scores, key=off_scores.get)
            signals_me.loc[date, best] = 1.0

    # Forward-fill monthly decisions to daily; gaps before first signal = 0 (cash)
    daily = signals_me.reindex(price_panel.index).ffill().fillna(0.0)
    weights.update(daily)
    return weights
