"""Harry Browne Permanent Portfolio — Session 9, 2026-07-16.

Philosophy: one strategy that survives all four economic regimes without
predicting which comes next.
  - Prosperity  (stocks rise, bonds flat): 25% SPY
  - Inflation   (hard assets up):          25% GLD
  - Deflation   (bonds surge, stocks fall): 25% TLT
  - Recession/fear (cash holds value):     25% SHY

Each quarter of the portfolio does well in exactly one regime and limps
through the other three, so the blend is always somewhere near flat-to-up.
When an asset class drifts far enough from its 25% target, rebalance back —
this enforces "buy low, sell high" mechanically across regimes.

CRITICAL DESIGN NOTE on missing-data periods:
Each slot is FIXED at 25% of the portfolio. When an asset is unavailable
(no listing yet), that slot sits in CASH rather than being redistributed
to other active assets. This is essential to preserve the regime-hedge
property — a 100% SPY portfolio during 2000-2002 (when TLT/GLD/SHY
weren't listed) would obliterate the strategy's founding premise.
The multi_engine cash sleeve credits T-bill yield on the idle fraction.

Research basis:
- Browne, H. (1998). "Fail-Safe Investing." St. Martin's Griffin.
- Rowland, C. & Lawson, J. M. (2012). "The Permanent Portfolio." Wiley.
- Bernstein, W. J. (2002). "The Four Pillars of Investing." McGraw-Hill.
- CraigRowland.com backtests (1972-2023): CAGR ~8%, max DD ~15% nominal.

Parameters (max 2):
  band  : fractional drift before triggering rebalance (default 0.05 = ±5%).
           0.0 = rebalance every month-end regardless of drift.
"""
import pandas as pd

DEFAULT_ASSETS = ["SPY", "TLT", "GLD", "SHY"]
TARGET_WEIGHT = 0.25          # FIXED slot per asset — never redistributed
DEFAULTS = {"band": 0.05}


def multi_signals(price_panel: pd.DataFrame, band: float = 0.05,
                  assets=None) -> pd.DataFrame:
    """Weight DataFrame (date x ticker): fixed-slot Permanent Portfolio.

    Each asset occupies a FIXED 25% slot.  When an asset is unavailable
    (NaN price on a given day), its 25% slot sits in CASH — it is NOT
    redistributed to the other active assets.  This preserves the
    regime-hedge construction property.

    Rebalancing: on each month-end, if any active asset's current weight
    deviates from its 25% target by more than `band`, all active slots
    are reset to 25% (a single multi-leg rebalance).  When band=0.0 the
    portfolio rebalances to 25%/slot every month-end.
    """
    assets = [a for a in (assets or DEFAULT_ASSETS) if a in price_panel.columns]
    weights = pd.DataFrame(0.0, index=price_panel.index,
                           columns=price_panel.columns)
    if not assets:
        return weights

    px = price_panel[assets].copy()

    month_ends = pd.Series(True, index=px.index).groupby(
        [px.index.year, px.index.month]).tail(1).index

    # Start with fixed-slot targets (25% each) but 0 for unavailable assets
    prev_w = pd.Series(0.0, index=assets)
    initialized = False

    for i, date in enumerate(px.index):
        has_data = px.loc[date].notna()
        active = [a for a in assets if has_data[a]]

        if not active:
            weights.loc[date, assets] = prev_w.values
            continue

        if not initialized:
            # First valid bar: assign TARGET_WEIGHT to each available asset
            w = pd.Series({a: TARGET_WEIGHT for a in active}, index=assets).fillna(0.0)
            initialized = True
        else:
            # Drift weights using today's return relative to yesterday
            prev_px = px.iloc[i - 1]
            w = prev_w.copy()
            for a in active:
                if pd.notna(prev_px[a]) and prev_px[a] > 0:
                    w[a] = prev_w[a] * (float(px.loc[date, a]) / float(prev_px[a]))
                # If newly listed (was NaN yesterday), assign its fixed slot
                elif not pd.notna(prev_px[a]):
                    w[a] = TARGET_WEIGHT

            # Rebalance at month-end when drift exceeds band
            if date in month_ends:
                target_w = pd.Series({a: TARGET_WEIGHT for a in active},
                                     index=assets).fillna(0.0)
                invested = w[active].sum()
                if invested > 0:
                    current_shares = w[active] / invested  # share of invested capital
                    target_shares = pd.Series(1.0 / len(active), index=active)
                    max_drift = (current_shares - target_shares).abs().max()
                else:
                    max_drift = 1.0
                if max_drift >= band:
                    w = target_w

            # Deactivate assets that lost data (shouldn't happen but safety)
            for a in assets:
                if not has_data[a]:
                    w[a] = 0.0

        # Safety: no single asset exceeds its fixed slot
        for a in active:
            w[a] = min(w[a], TARGET_WEIGHT)

        prev_w = w.copy()
        weights.loc[date, assets] = w.values

    # Safety: row sums must not exceed 1
    s = weights.sum(axis=1)
    over = s > 1.0
    if over.any():
        weights.loc[over] = weights.loc[over].div(s[over], axis=0)
    return weights
