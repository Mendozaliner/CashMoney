"""Short-term mean-reversion strategies on SPY (session 11, 2026-07-17).

Charter queue item: "mean reversion (RSI-2, Bollinger)". Three families, each
long-only, binary exposure, gated by the 200-day SMA uptrend filter (Connors'
own recommendation; also consistent with this desk's E5/E11/E16 finding that
un-gated signals crash in bears).

Sources (see research/2026-07-17-mean-reversion.md):
- Connors & Alvarez, "Short Term Trading Strategies That Work" (2008): RSI(2)
  <5/10 entries on S&P, exit on strength; 200d SMA filter; no stops.
- Pagonidis, "The IBS Effect: Mean Reversion in Equity ETFs" (NAAIM 2013):
  IBS = (C-L)/(H-L); avg next-day return +0.35% when IBS<0.2, -0.13% when >0.8.
- Price Action Lab (2018): RSI(2) edge is likely a data-mined artifact --
  the desk's skeptical prior.
- Bollinger mean reversion: SSRN 5713082 / Atlantis 125991306 -- lower-band
  entries on index ETFs, exit at middle band.

Timing contract: signals computed at close t are filled at close t+1 by the
vector engine (signal.shift(2) vs close-to-close returns). This is an HONEST
handicap for 1-3 day mean reversion: the desk trades EOD, never intraday.

Max 2 tunable parameters per family. RSI period fixed at 2; Bollinger
lookback fixed at 20; SMA gate fixed at 200d (no band).
"""
import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """Wilder RSI. Uses only data up to and including t (no lookahead)."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ru = up.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rd = dn.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = ru / rd.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.fillna(50.0)


def _hold_state(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    """Stateful long/flat: go long on entry-True, flat on exit-True."""
    sig = pd.Series(np.nan, index=entry.index)
    sig[entry] = 1.0
    sig[exit_ & ~entry] = 0.0
    return sig.ffill().fillna(0.0)


def rsi2_signals(close: pd.Series, entry_lvl: float = 10.0,
                 exit_lvl: float = 70.0) -> pd.Series:
    """Connors RSI(2): long when RSI2 < entry_lvl AND close > SMA200;
    exit when RSI2 > exit_lvl or trend gate turns off."""
    rsi = _rsi(close, 2)
    sma200 = close.rolling(200).mean()
    gate = close > sma200
    entry = (rsi < entry_lvl) & gate
    exit_ = (rsi > exit_lvl) | ~gate
    return _hold_state(entry, exit_)


def bollinger_signals(close: pd.Series, k: float = 2.0,
                      exit_at: str = "mid") -> pd.Series:
    """Bollinger(20, k) mean reversion: long when close < mid - k*sd AND
    close > SMA200; exit when close >= mid ('mid') or >= mid + 0.5*sd
    ('upper_half'), or the trend gate turns off."""
    mid = close.rolling(20).mean()
    sd = close.rolling(20).std()
    sma200 = close.rolling(200).mean()
    gate = close > sma200
    entry = (close < mid - k * sd) & gate
    exit_px = mid if exit_at == "mid" else mid + 0.5 * sd
    exit_ = (close >= exit_px) | ~gate
    return _hold_state(entry, exit_)


def ibs_signals(ohlc: pd.DataFrame, entry_lvl: float = 0.2,
                exit_lvl: float = 0.8) -> pd.Series:
    """Pagonidis IBS: IBS=(C-L)/(H-L). Long when IBS < entry_lvl AND
    close > SMA200; exit when IBS > exit_lvl or trend gate off."""
    c, h, l = ohlc["Close"], ohlc["High"], ohlc["Low"]
    rng = (h - l).replace(0.0, np.nan)
    ibs = ((c - l) / rng).fillna(0.5)
    sma200 = c.rolling(200).mean()
    gate = c > sma200
    entry = (ibs < entry_lvl) & gate
    exit_ = (ibs > exit_lvl) | ~gate
    return _hold_state(entry, exit_)
