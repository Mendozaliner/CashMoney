"""Variance Risk Premium (VRP) Confidence Layer on v2 (session 26, E40).

The Variance Risk Premium = implied variance (from VIX) - realized variance.
It measures the fear premium investors pay for protection. Academic evidence
shows that high VRP predicts positive near-term equity returns, while
compressed VRP (complacency) predicts below-average returns.

Philosophy: scale DOWN the v2 vol-target exposure modestly when VRP is
BELOW its rolling median (compressed fear premium / complacency), and
leave exposure unchanged when VRP is at or above its median (normal or
elevated fear premium = equity-positive regime).

This is the OPPOSITE of E2 (VIX level de-risking, CLOSED):
- E2 reduced exposure when VIX was HIGH → wrong direction (high VIX
  precedes high returns; note from STATE.md: "High VIX precedes high returns")
- E40 reduces exposure when VRP is LOW (complacency), keeping full
  exposure when the market is appropriately fearful.

Key distinction from other closed families:
- E2 (VIX percentile): used VIX LEVEL as de-risk trigger → CLOSED
- E29 (VIX-regime ensemble): VIX > threshold → switch strategies → CLOSED
- E40 uses VIX² - realized_vol² as a CONFIDENCE MULTIPLIER on v2 exposure;
  the base v2 mechanism is unchanged; VRP only scales the vol-target fraction.

Academic basis:
- Bollerslev, Tauchen & Zhou (2009, NBER 15022): VRP predicts equity excess
  returns significantly at 1-4 week horizons; R² ~7% at 1-month horizon.
- Carr & Wu (2009, JFE 74): time-varying VRP documents the compensation
  investors require for bearing variance risk; positively autocorrelated.
- Bekaert & Hoerova (2014, JFE 111): VRP subsumes VIX level in predicting
  equity returns; VIX = VRP + expected realized vol.
- Dew-Becker et al. (2017, JFE 123): the predictive content of VRP for
  equity returns is robust to different realized-vol estimation windows.
- Bollerslev & Todorov (2011, JFE): VRP reflects jump tail risk premium;
  explains equity premium dynamics better than VIX alone.

Tunable parameters (max 2): vrp_lb, vrp_scale.
v2 anchor parameters (target_vol=0.18, lookback=20) are FIXED at champion values.
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

TRADING_DAYS = 252
DEFAULTS = {"vrp_lb": 63, "vrp_scale": 0.75}


def _compute_vrp(spy_close: pd.Series, vix_close: pd.Series) -> pd.Series:
    """Variance Risk Premium = implied variance - realized variance (both annualized).

    VRP > 0: market is paying a fear premium (implied > realized) — normal.
    VRP < 0: complacency (implied < realized) — rare and equity-negative.
    Rolling position vs own median: consistently below median = compressed premium.

    Timing: VRP at bar t uses VIX close at t and realized vol through t.
    Shift applied in signals() before use.
    """
    spy_ret = spy_close.pct_change().fillna(0.0)
    # 20-day realized variance, annualized
    realized_var = spy_ret.rolling(20).var() * TRADING_DAYS
    # Implied variance from VIX (VIX is annualized % vol: VIX/100 = annual vol)
    vix_aligned = vix_close.reindex(spy_close.index, method="ffill")
    implied_var = (vix_aligned / 100.0) ** 2
    return implied_var - realized_var


def signals(close: pd.Series,
            vrp_lb: int = 63,
            vrp_scale: float = 0.75,
            target_vol: float = 0.18,
            lookback: int = 20) -> pd.Series:
    """VRP-modulated v2 exposure.

    Base: v2 vol-target signal (SMA200/3% trend × min(1, target_vol/realized_vol)).
    Modifier: if VRP is below its rolling vrp_lb-day median, scale base by vrp_scale.
    No modification when trend gate is 0 (already in cash).

    Shift: VRP and its median computed at bar t; shift(1) so the regime flag
    for bar t is used at bar t+1, consistent with the no-lookahead contract.
    """
    # Base v2 signal
    base_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)

    # VRP calculation
    vix = load_ohlcv("^VIX")["Close"]
    vrp = _compute_vrp(close, vix)

    # Rolling median of VRP (vrp_lb-day)
    vrp_median = vrp.rolling(vrp_lb).median()

    # Regime: 1 = VRP above median (fear premium elevated, full confidence)
    #         0 = VRP below or equal to median (complacency, scale down)
    # shift(1): regime known at t, acted on at t+1
    high_vrp = (vrp > vrp_median).astype(float).shift(1).fillna(1.0)

    # Scale: full exposure in high-VRP regime, vrp_scale in low-VRP regime
    scale = high_vrp + (1.0 - high_vrp) * vrp_scale

    return (base_sig * scale).clip(0.0, 1.0)
