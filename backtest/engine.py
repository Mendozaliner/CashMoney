"""Backtest engine: thin wrapper around backtesting.py (kernc).

Input is a close-only total-return series plus a precomputed 0/1 signal
series (see strategies/base.py for the causality contract). We synthesize
OHLC with O=H=L=C; backtesting.py fills orders at the *next* bar's open,
which for synthetic bars equals the next close -- i.e. a signal computed on
bar t trades at bar t+1. Combined with the signal contract this rules out
lookahead by construction (and by unit test).

Costs: `commission` (default 0.1% per trade side) applied by backtesting.py.
Cash earns 0% while flat (conservative vs. T-bills).
"""
import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

TRADING_DAYS = 252


def _ohlc(close: pd.Series, signal: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close,
         "Volume": 1e9, "Signal": signal.reindex(close.index).values}
    )
    return df


class _SignalStrategy(Strategy):
    def init(self):
        self.sig = self.I(
            lambda: self.data.df["Signal"].values, name="signal", plot=False
        )

    def next(self):
        s = self.sig[-1]
        if s > 0 and not self.position:
            self.buy()
        elif s == 0 and self.position:
            self.position.close()


def run(close, signal, cash=100_000_000, commission=0.001):
    """Run backtesting.py on a (close, signal) pair. Returns (stats, bt).

    The close series is normalized to start at 100 so that whole-share
    order sizing in backtesting.py never materially distorts results
    (the raw input is a growth index reaching ~4e5).
    """
    close = close / close.iloc[0] * 100.0
    bt = Backtest(
        _ohlc(close, signal), _SignalStrategy,
        cash=cash, commission=commission,
        exclusive_orders=False, trade_on_close=False, finalize_trades=True,
    )
    return bt.run(), bt


def metrics(close, signal, commission=0.001, label="") -> dict:
    """Headline metrics computed from the engine's equity curve."""
    stats, _ = run(close, signal, commission=commission)
    eq = stats._equity_curve["Equity"]
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    sharpe = r.mean() / r.std() * np.sqrt(TRADING_DAYS) if r.std() > 0 else 0.0
    downside = r[r < 0].std()
    sortino = (r.mean() * TRADING_DAYS / (downside * np.sqrt(TRADING_DAYS))
               if downside and downside > 0 else np.nan)
    n_trades = stats["# Trades"]
    return {
        "label": label,
        "CAGR": round(cagr * 100, 2),
        "Sharpe": round(float(sharpe), 3),
        "Sortino": round(float(sortino), 3),
        "MaxDD": round(stats["Max. Drawdown [%]"], 2),
        "WinRate": round(stats["Win Rate [%]"], 1) if n_trades else np.nan,
        "Trades": int(n_trades),
        "Trades/yr": round(n_trades / years, 1),
        "End$per1k": round(1000 * eq.iloc[-1] / eq.iloc[0], 2),
    }


def buy_and_hold_signal(close: pd.Series) -> pd.Series:
    return pd.Series(1.0, index=close.index)
