"""True Antonacci Global Equity Momentum (GEM) — international equity rotation.

Implements the original GEM paper with international equity alternatives, unlike
dual_momentum.py (discarded E3/E7) which only rotated among domestic indices
SPY/QQQ/DIA. The key innovation is TRUE global equity rotation across borders.

Equity candidates: SPY (US large cap), EFA (Developed ex-US), EEM (Emerging markets)
Absolute bar:      SHY (3-month T-bills — short duration to avoid rising-rate risk)
Defensive harbor:  AGG (investment grade bonds, ~6yr duration vs TLT's >15yr;
                   avoids the 2022 duration catastrophe that killed E3)

Rule (Antonacci 2014 GEM):
  1. Compute lookback-skip return for SPY, EFA, EEM (equity candidates).
  2. Compute the same for SHY (absolute momentum bar).
  3. If max(equity momenta) > SHY momentum → 100% in best equity (by momentum).
     Else → 100% in AGG (defensive harbor).

Research basis:
- Antonacci, G. (2014). "Dual Momentum Investing." McGraw-Hill.
  Original GEM backtested to 1974: ~17% CAGR, ~25% MaxDD vs SPY ~50%.
  SSRN 2042750 (2012): excess returns over T-bills through international rotation.
- Geczy & Samonov (2016). "Two Centuries of Price-Return Momentum." FAJ 72(5).
  International equity momentum robust over 200 years.
- Country rotation: Harvey & Siddique (2000). "Conditional Skewness in Asset
  Pricing Tests." J. Finance 55(3). International diversification reduces
  skewness risk that pure domestic momentum leaves unhedged.
- AGG vs TLT harbor: AGG (AGG duration ~6yr, core IG bonds) avoids the 2022
  problem where TLT lost 33% in a rate-rising environment while SPY lost 18%.
  SHY absolute bar further guards against entering bonds in bear markets.
- Skeptical prior: Barroso & Santa-Clara (2015) momentum crashes; Daniel &
  Moskowitz (2016) crash risk in momentum. The SHY absolute bar is the defense.
  EEM truncates fold 1 to ~2003+; results before that use SPY/EFA only.

Key difference from failed E3/E7:
  E3: rotated SPY/QQQ/DIA (all US) → AGG/TLT (TLT crashed 2022, -33%).
  E7: same rotation, switched harbor to SHY → absolute bar too passive.
  GEM: rotates across BORDERS (US vs Developed vs Emerging) → AGG harbor.
  International cross-country rotation is the missing piece, not just harbor choice.

Data constraints:
  EFA: 2001-08+ (fold 1 truncated to 2001-08)
  EEM: 2003-04+ (fold 1 more truncated; SPY/EFA rotate until EEM available)
  AGG: 2003-09+ (SHY used as fallback defensive before AGG available)

Interface: multi_signals(price_panel, lookback, skip) -> pd.DataFrame (weights).
Parameters (max 2): lookback (momentum window, days), skip (skip-month, days).
"""
import pandas as pd

EQUITY_CANDIDATES = ["SPY", "EFA", "EEM"]
ABSOLUTE_BAR = "SHY"
DEFENSIVE = "AGG"
FALLBACK_DEFENSIVE = "SHY"

DEFAULTS = {"lookback": 252, "skip": 21}


def multi_signals(price_panel: pd.DataFrame, lookback: int = 252,
                  skip: int = 21) -> pd.DataFrame:
    """Return weight DataFrame (date × ticker) for True Global Equity Momentum.

    Only tickers present in price_panel.columns are used. Missing equity
    candidates (e.g. EEM before 2003) are handled gracefully — the strategy
    uses whatever equity candidates have valid momentum at each date.
    Rows before the warmup period are left at zero (stay in cash).
    """
    available_eq = [t for t in EQUITY_CANDIDATES if t in price_panel.columns]
    shy = ABSOLUTE_BAR if ABSOLUTE_BAR in price_panel.columns else None
    defensive = (DEFENSIVE if DEFENSIVE in price_panel.columns
                 else FALLBACK_DEFENSIVE if FALLBACK_DEFENSIVE in price_panel.columns
                 else None)

    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)

    if not available_eq or not shy or not defensive:
        return weights

    window = max(lookback - skip, 1)
    mom = price_panel.pct_change(window).shift(skip)

    eq_mom = mom[available_eq]
    best_mom = eq_mom.max(axis=1, skipna=True)

    valid_rows_mask = eq_mom.notna().any(axis=1)
    best_ticker = pd.Series(index=price_panel.index, dtype=object)
    if valid_rows_mask.any():
        best_ticker[valid_rows_mask] = eq_mom.loc[valid_rows_mask].idxmax(axis=1)

    shy_mom = mom[shy]
    valid = best_mom.notna() & shy_mom.notna()

    in_equity = valid & (best_mom > shy_mom)
    in_defensive = valid & ~in_equity

    for ticker in available_eq:
        weights.loc[in_equity & (best_ticker == ticker), ticker] = 1.0

    if defensive in weights.columns:
        weights.loc[in_defensive, defensive] = 1.0

    return weights
