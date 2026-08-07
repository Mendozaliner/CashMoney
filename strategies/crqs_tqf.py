"""CRQS + Trend Quality Filter (session 31, E46).

Extends the CRQS champion with a variance-ratio-based Trend Quality Filter
(TQF) that reduces equity exposure in choppy, low-autocorrelation markets
where the SMA200 trend signal is more likely to whipsaw.

Strategy pipeline per day:
    a. CRQS multi_signals: SPY, IEF, GLD weights (champion E42 logic).
    b. TQF multiplier: compute VR(q, window) on SPY returns.
       When VR > 1.0 (trending):     equity_sig unchanged.
       When VR ≤ 1.0 (choppy):       equity_sig × tqf_scale.
    c. Defensive sleeve: IEF/GLD weights scaled proportionally so
       weights still sum to ≤ 1.0.

Research hypothesis
-------------------
The SMA200 filter inside vol_target generates crossover signals that are
more profitable in trending regimes (H > 0.5, VR > 1). In choppy markets,
these signals are noise. The TQF prevents the strategy from chasing false
crossovers in mean-reverting environments, reducing drawdown and turnover
while forfeiting only the (noisier) choppy-market returns.

Expected effect: lower turnover, improved Sharpe, flatter drawdown profile.
Possible failure mode: choppy periods often precede trend reversals — scaling
down equity pre-emptively gives away the first leg of a new trend.

Tunable parameters (12 configs = 3 × 2 × 2):
    vr_q      ∈ {10, 20, 40}  — variance ratio aggregation horizon (days)
    vr_lb     ∈ {63, 126}     — rolling estimation window (days)
    tqf_scale ∈ {0.50, 0.75}  — equity multiplier in choppy regime

CRQS parameters are held fixed at champion values:
    eps_threshold=0.00, scale_down=0.75, corr_threshold=0.00
    corr_lb=63, target_vol=0.18, lookback=20

References
----------
Lo, A.W., MacKinlay, A.C. (1988). "Stock Market Prices Do Not Follow Random
  Walks: Evidence from a Simple Specification Test". Rev. Fin. Studies, 1(1).
Peters, E.E. (1991). "Chaos and Order in Capital Markets". Wiley.
Chan, E.P. (2013). "Algorithmic Trading". Wiley, ch. 3.
Moskowitz, T., Ooi, Y.H., Pedersen, L.H. (2012). "Time Series Momentum".
  Journal of Financial Economics, 104(2), 228–250. (TQF is complementary
  to their finding that trend-following works in persistent regimes.)
"""
import numpy as np
import pandas as pd

from strategies.crqs import multi_signals as crqs_signals
from tools.trend_quality import variance_ratio_signal
from data.loader import load_ohlcv

DEFAULTS = {
    "vr_q": 20,
    "vr_lb": 63,
    "tqf_scale": 0.50,
    # CRQS champion parameters (fixed)
    "eps_threshold": 0.00,
    "scale_down": 0.75,
    "corr_threshold": 0.00,
    "corr_lb": 63,
    "target_vol": 0.18,
    "lookback": 20,
}


def multi_signals(close: pd.Series,
                  shiller: pd.DataFrame,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  vr_q: int = DEFAULTS["vr_q"],
                  vr_lb: int = DEFAULTS["vr_lb"],
                  tqf_scale: float = DEFAULTS["tqf_scale"],
                  eps_threshold: float = DEFAULTS["eps_threshold"],
                  scale_down: float = DEFAULTS["scale_down"],
                  corr_threshold: float = DEFAULTS["corr_threshold"],
                  corr_lb: int = DEFAULTS["corr_lb"],
                  target_vol: float = DEFAULTS["target_vol"],
                  lookback: int = DEFAULTS["lookback"]) -> pd.DataFrame:
    """Weight schedule for CRQS + Trend Quality Filter (E46).

    Returns a DataFrame with columns ['SPY', 'IEF', 'GLD'] where weights
    sum to at most 1.0 (remainder earns risk-free rate).

    The TQF multiplier is applied to the SPY weight from CRQS; IEF and GLD
    weights are re-scaled proportionally from the freed cash (i.e., the
    defensive sleeve can absorb the extra cash released by TQF throttling,
    subject to their SMA200 gates already applied inside crqs_signals).

    Timing: TQF multiplier at bar t uses VR computed from data through t
    (same close used for vol_target), then shift(1) inside
    variance_ratio_signal ensures execution at bar t+1 — consistent with
    the CRQS timing contract.

    Args:
        close         : SPY daily adjusted close.
        shiller       : Shiller monthly DataFrame from load_shiller().
        ief           : IEF daily close (loaded if None).
        gld           : GLD daily close (loaded if None).
        vr_q          : Variance ratio aggregation horizon (days).
        vr_lb         : Rolling estimation window (days).
        tqf_scale     : Equity multiplier in non-trending regime (0 < x ≤ 1).
        eps_threshold : EPS 12m growth below which quality gate fires.
        scale_down    : Equity weight multiplier when EPS gate fires.
        corr_threshold: Rolling SPY-IEF corr above which → GLD hedge.
        corr_lb       : Days for rolling stock-bond correlation.
        target_vol    : Vol-target annual volatility.
        lookback      : Vol-target lookback in days.
    """
    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]

    # ── 1. CRQS base weights ────────────────────────────────────────────────
    crqs_w = crqs_signals(
        close, shiller, ief=ief, gld=gld,
        eps_threshold=eps_threshold,
        scale_down=scale_down,
        corr_threshold=corr_threshold,
        corr_lb=corr_lb,
        target_vol=target_vol,
        lookback=lookback,
    )

    # ── 2. Trend Quality Filter multiplier ─────────────────────────────────
    spy_ret = close.pct_change().fillna(0.0)
    tqf_mult = variance_ratio_signal(spy_ret, q=vr_q, window=vr_lb,
                                     tqf_scale=tqf_scale)
    tqf_mult = tqf_mult.reindex(close.index, method="ffill").fillna(1.0)

    # ── 3. Apply TQF to equity; defensive sleeve re-scaled ─────────────────
    spy_w_raw = (crqs_w["SPY"] * tqf_mult).clip(0.0, 1.0)

    # Extra cash freed by TQF: distribute proportionally to existing IEF/GLD
    extra_cash = (crqs_w["SPY"] - spy_w_raw).clip(0.0, None)
    existing_def = (crqs_w["IEF"] + crqs_w["GLD"]).clip(1e-10, None)
    ief_extra = extra_cash * (crqs_w["IEF"] / existing_def).fillna(0.0)
    gld_extra = extra_cash * (crqs_w["GLD"] / existing_def).fillna(0.0)

    ief_w = (crqs_w["IEF"] + ief_extra).clip(0.0, 1.0)
    gld_w = (crqs_w["GLD"] + gld_extra).clip(0.0, 1.0)

    # Ensure total weight ≤ 1.0
    total = spy_w_raw + ief_w + gld_w
    scale = (1.0 / total).clip(upper=1.0)
    spy_w_raw = spy_w_raw * scale
    ief_w = ief_w * scale
    gld_w = gld_w * scale

    return pd.DataFrame(
        {"SPY": spy_w_raw, "IEF": ief_w, "GLD": gld_w},
        index=close.index,
    )
