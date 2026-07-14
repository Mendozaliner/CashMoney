"""Dual Momentum strategy (Antonacci 2014) adapted for the CashMoney universe.

Philosophy: Combine absolute momentum (time-series — does the best equity beat
T-bills?) with relative momentum (cross-sectional — which equity is strongest?).
The combination sidesteps equity bear markets entirely (goes to bonds) while
rotating to the strongest equity in bull markets.

Rule (adapted from Antonacci's Global Equity Momentum / GEM):
  1. Compute lookback-skip return for SPY, QQQ, DIA (equity candidates).
  2. Compute the same momentum for SHY (3-month T-bill ETF = absolute bar).
  3. If best_equity_momentum > SHY_momentum → 100% in the best equity.
     Else → 100% in TLT (intermediate-duration bonds, defensive harbor).
  Signal is daily (continuous); execution cost applies only when allocation
  actually changes, which in practice is a few times per year.

Research basis:
- Antonacci, G. (2014). "Dual Momentum Investing." McGraw-Hill.
- Antonacci, G. (2012). "Risk Premia Harvesting Through Dual Momentum."
  SSRN 2042750. Backtested 1971-2011; 17.4% CAGR, MaxDD -22% vs SPY -51%.
- Jegadeesh & Titman (1993). "Returns to Buying Winners and Selling Losers."
  J. Finance 48(1). Cross-sectional momentum across 3-12 months is robust.
- Asness, Moskowitz & Pedersen (2013). "Value and Momentum Everywhere."
  J. Finance 68(3). Momentum premium pervasive across asset classes.
- Geczy & Samonov (2016). "Two Centuries of Price-Return Momentum."
  FAJ 72(5). Long-horizon robustness in price momentum.
- Skeptical prior: momentum crashes (Barroso & Santa-Clara 2015) and
  the 2009 reversal (Daniel & Moskowitz 2016). Hence strict evaluation bar.

Interface: multi_signals(price_panel, lookback, skip) -> pd.DataFrame (weights).
Parameters (max 2): lookback (momentum window, days), skip (skip-month, days).
"""
import pandas as pd

EQUITY_ASSETS = ["SPY", "QQQ", "DIA"]
DEFENSIVE_ASSET = "TLT"
ABSOLUTE_BAR_ASSET = "SHY"

DEFAULTS = {"lookback": 252, "skip": 21}


def multi_signals(price_panel: pd.DataFrame, lookback: int = 252,
                  skip: int = 21, defensive: str | None = None) -> pd.DataFrame:
    """Return a weight DataFrame (date × ticker) for Dual Momentum.

    Only tickers present in price_panel.columns are used. Rows before the
    warmup period (first lookback days) are left at zero (stay in cash).
    """
    available_eq = [t for t in EQUITY_ASSETS if t in price_panel.columns]
    defensive = defensive or DEFENSIVE_ASSET
    defensive = defensive if defensive in price_panel.columns else None
    abs_bar = ABSOLUTE_BAR_ASSET if ABSOLUTE_BAR_ASSET in price_panel.columns else None

    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)

    if not available_eq or not defensive:
        return weights

    # Momentum at t = total return from t-lookback to t-skip
    # pct_change(lookback-skip) = (close[t] / close[t-(lookback-skip)]) - 1
    # then shift(skip) so the window ends skip days in the past
    window = max(lookback - skip, 1)
    mom = price_panel.pct_change(window).shift(skip)

    eq_mom = mom[available_eq]
    best_mom = eq_mom.max(axis=1, skipna=True)

    # idxmax raises on all-NaN rows; filter to valid rows first
    valid_rows_mask = eq_mom.notna().any(axis=1)
    best_ticker = pd.Series(index=price_panel.index, dtype=object)
    if valid_rows_mask.any():
        best_ticker[valid_rows_mask] = eq_mom.loc[valid_rows_mask].idxmax(axis=1)

    shy_mom = mom[abs_bar] if abs_bar else pd.Series(0.0, index=price_panel.index)

    # Valid rows: enough history for the momentum calculation
    valid = best_mom.notna() & shy_mom.notna()

    # Equity mode: best equity beats T-bills on absolute momentum
    in_equity = valid & (best_mom > shy_mom)
    in_defensive = valid & ~in_equity

    # Assign weights: one ticker gets 1.0 per row (one-hot style)
    for ticker in available_eq:
        weights.loc[in_equity & (best_ticker == ticker), ticker] = 1.0

    if defensive in weights.columns:
        weights.loc[in_defensive, defensive] = 1.0

    return weights
