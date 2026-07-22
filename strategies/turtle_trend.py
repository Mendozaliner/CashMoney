"""Turtle Trading — Donchian channel breakout + vol-target overlay (E26).

Philosophy: Richard Dennis & William Eckhardt trained the Turtle Traders in 1983,
proving systematic trend-following via price CHANNEL breakouts is repeatable.
The insight: use the actual price HIGH/LOW over N days, not a lagging average.

System 2 (the longer-term, lower-churn version):
  Entry: today's close > maximum of prior entry_channel closes (new N-day high)
  Exit:  today's close < minimum of prior (entry_channel // 2) closes
  Vol overlay: scale by target_vol / realized_vol, capped at 1.0 — same overlay
               as champion v2; critical during volatility spikes (Barroso & Santa-Clara 2015).

The channel signal is causal and vectorized using a forward-fill trick:
  raw = NaN everywhere; set 1.0 where close > channel_high; set 0.0 where
  close < channel_low; forward-fill. This exactly replicates the Turtle state machine
  (hold position until channel_low is breached).

Why this differs from SMA200 (the champion's trend gate):
  - SMA200 lags: it responds to all 200 prior closes equally
  - Donchian responds to the actual EXTREME price reached, not the average
  - SMA200 has only one threshold; Donchian uses asymmetric entry/exit channels
  - Historical edge: Faber (2007) showed channel rules outperform SMA in commodities;
    Jez Liberty (2012) confirmed across equity and commodity futures

Research basis:
  - Faith, C. (2003). "Way of the Turtle." McGraw-Hill.
  - Faber, M. (2007). "A Quantitative Approach to Tactical Asset Allocation." JPM.
  - Baz, J. et al. (2015). "Dissecting Investment Strategies in the Cross-Section
    and Time Series." SSRN 2695101. Trend via channel beats momentum indices.
  - Barroso & Santa-Clara (2015). "Momentum has its Moments." JFE.
    Momentum crashes during vol spikes → vol overlay is critical.
  - Hurst, Ooi & Pedersen (2017). "A Century of Evidence on Trend-Following Investing."
    J. Portfolio Management. Trend-following works across 100 years.

Unsuccessful philosophies reviewed:
  - Sector momentum crash (E5/E11): channel entry with SMA200 gate avoids this because
    the gate prevents entry during downtrends regardless of channel signal
  - Mean reversion (E17-E19): channel is pure trend-following, zero mean-reversion decay

Parameters (max 2): entry_channel (N-day max), vol_target (annualized).
Exit channel is fixed at entry_channel // 2 (standard Turtle System 2 ratio).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _donchian_signal(close: pd.Series, entry: int, exit_ch: int) -> pd.Series:
    """Causal, vectorized Donchian channel long/flat signal.

    Entry when close exceeds the prior-entry-period high (excludes today).
    Exit when close falls below the prior-exit-period low (excludes today).
    Between entry and exit: hold prior state via ffill.
    """
    channel_high = close.shift(1).rolling(entry, min_periods=entry).max()
    channel_low  = close.shift(1).rolling(exit_ch, min_periods=exit_ch).min()

    raw = pd.Series(np.nan, index=close.index)
    raw[close > channel_high] = 1.0
    raw[close < channel_low]  = 0.0
    return raw.ffill().fillna(0.0)


def signals(close: pd.Series, entry_channel: int = 55,
            vol_target: float = 0.18) -> pd.Series:
    """Donchian breakout trend signal with vol-targeting overlay.

    Parameters (max 2):
        entry_channel : Days for channel entry. Exit = entry_channel // 2.
                        20 = fast (Turtle System 1 entry width)
                        55 = classic (Turtle System 2)
                        100 = slow (lower turnover, longer trends)
        vol_target    : Annualized realized-vol target for exposure scaling.
                        Uses 20-day rolling realized vol (matching champion v2).
    """
    exit_ch = max(entry_channel // 2, 5)
    trend = _donchian_signal(close, entry_channel, exit_ch)
    rv = close.pct_change().rolling(20, min_periods=10).std() * np.sqrt(TRADING_DAYS)
    scale = (vol_target / rv).clip(upper=1.0)
    return (trend * scale).fillna(0.0).clip(0.0, 1.0)
