"""Correlation-Regime Defensive Switch (session 23, E35).

Uses the rolling correlation between SPY and IEF daily returns as a
regime detector to dynamically select between IEF (bonds) and GLD (gold)
as the defensive cash-sleeve asset when v2 is out of equities.

Philosophy (Ilmanen 2011 / Asness et al. 2022):
The stock-bond correlation is the key dividing line between two macro regimes:

  DEFLATION / RECESSION regime (negative or low corr):
    Bonds rally when stocks fall (flight to quality). IEF is the best hedge.
    Example: 2000-2002 (dot-com bust), 2008-09 (GFC), 2020 (COVID crash).

  INFLATION regime (positive corr):
    Both stocks AND bonds fall together; gold provides the hedge.
    Example: 1970s stagflation, 2022 (Fed hiking cycle) when IEF -18%
    but GLD ended +0.4% while SPY was -18%.

The signal: if rolling corr(SPY_ret, IEF_ret) over corr_lb days
exceeds corr_threshold, we are in "inflation regime" → use GLD as defensive.
Otherwise "normal regime" → use IEF as defensive (gated by IEF SMA).

Key distinctions from prior experiments:
- E33 TB (s22): IEF-only defensive, no regime awareness. Failed in 2022.
- E34 DDAS (s23): structural 50/50 split; doesn't adapt to regime.
- E29 VIX-Regime Ensemble (CLOSED, s20): used VIX levels to switch
  between CTA and v2. E35 uses stock-bond CORRELATION — different signal.
  VIX was too correlated to the equity gate itself (corr_v2=0.967).
  Stock-bond correlation is an INDEPENDENT signal not captured by SPY SMA200.
- E30 Inter-Market (CLOSED, s20): compared bond vs equity performance.
  E35 uses correlation of their RETURNS — different construction.

Academic basis:
- Ilmanen (2011) "Expected Returns" Ch. 17: stock-bond correlation switches
  between negative (inflation < 3.5%) and positive (inflation > 3.5%); the
  switch has dramatic implications for portfolio construction.
- Asness, Frazzini & Heje Pedersen (2012) JPM: stock-bond correlation is
  negative in recessions and positive in inflation regimes; simple rolling
  correlation identifies the regime with reasonable accuracy.
- Campbell, Pflueger & Viceira (2020) RFS: real stock-bond correlation
  depends on monetary policy framework and inflation uncertainty.
- Baele, Bekaert & Inghelbrecht (2010) RFS: time-varying stock-bond
  correlation explained by macro factors; flight-to-quality regimes.
- Practitioner validation: 2022 was the worst year for a 60/40 portfolio
  in 50 years precisely because the stock-bond correlation flipped positive.

Tunable parameters (max 2): corr_lb, corr_threshold.
"""
import numpy as np
import pandas as pd

from strategies import vol_target
from data.loader import load_ohlcv

DEFAULTS = {"corr_lb": 63, "corr_threshold": 0.15}

_IEF_SMA_WINDOW = 200
_GLD_SMA_WINDOW = 200


def multi_signals(close: pd.Series,
                  ief: pd.Series | None = None,
                  gld: pd.Series | None = None,
                  corr_lb: int = 63,
                  corr_threshold: float = 0.15,
                  target_vol: float = 0.18,
                  lookback: int = 20) -> pd.DataFrame:
    """Weight schedule for v2 (SPY) + correlation-regime-switched defensive.

    Returns DataFrame with columns ['SPY', 'IEF', 'GLD'] where:
      SPY weight = v2 signal (unchanged, always).
      When v2 is in cash (SPY < SMA200+band):
        - If rolling corr(SPY_ret, IEF_ret) < corr_threshold (normal regime):
            IEF weight = cash_avail × ief_sma_gate
        - If rolling corr(SPY_ret, IEF_ret) >= corr_threshold (inflation):
            GLD weight = cash_avail × gld_sma_gate
        Unused defensive fraction earns T-bill rate.

    Timing: correlation computed at day t uses data through t; the regime
    flag is shifted(1) so the defensive switch executes at t+1 (next day).
    The SMA gates are also shifted(1) per standard no-lookahead convention.

    Args:
        close          : SPY daily adjusted close.
        ief            : IEF daily adjusted close (loaded if None).
        gld            : GLD daily adjusted close (loaded if None).
        corr_lb        : Rolling window in days for SPY-IEF correlation.
        corr_threshold : If rolling corr >= this, switch to GLD defensive.
        target_vol     : V2 vol target (champion 0.18, fixed).
        lookback       : V2 realized-vol lookback (champion 20, fixed).
    """
    spy_sig = vol_target.signals(close, target_vol=target_vol, lookback=lookback)
    cash_avail = (1.0 - spy_sig).clip(0.0, 1.0)

    if ief is None:
        ief = load_ohlcv("IEF")["Close"]
    if gld is None:
        gld = load_ohlcv("GLD")["Close"]

    ief_a = ief.reindex(close.index, method="ffill")
    gld_a = gld.reindex(close.index, method="ffill")

    spy_ret = close.pct_change().fillna(0.0)
    ief_ret = ief_a.pct_change().fillna(0.0)

    # Rolling correlation between SPY and IEF daily returns
    # High positive correlation → inflation regime → GLD
    rolling_corr = spy_ret.rolling(corr_lb).corr(ief_ret).fillna(0.0)

    # Regime flag: 1 = inflation (positive stock-bond correlation)
    # shift(1): regime known at close of day t, act at t+1
    inflation_flag = (rolling_corr >= corr_threshold).astype(float).shift(1).fillna(0.0)
    normal_flag = 1.0 - inflation_flag

    # Defensive SMA trend gates (each independent, shift(1) for no-lookahead)
    ief_gate = (ief_a > ief_a.rolling(_IEF_SMA_WINDOW).mean()).astype(float).shift(1).fillna(0.0)
    gld_gate = (gld_a > gld_a.rolling(_GLD_SMA_WINDOW).mean()).astype(float).shift(1).fillna(0.0)

    # Allocate defensive cash based on regime
    ief_weight = cash_avail * normal_flag * ief_gate
    gld_weight = cash_avail * inflation_flag * gld_gate

    return pd.DataFrame(
        {"SPY": spy_sig, "IEF": ief_weight, "GLD": gld_weight},
        index=close.index,
    )
