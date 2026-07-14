"""Drawdown kill-switch overlay on an existing single-asset signal (session 5).

Philosophy: Even the best strategies can blow up if they ride a large drawdown
without an exit rule. The kill-switch goes to 100% cash when the simulated
portfolio equity falls below a drawdown threshold, and re-enters only after
a partial recovery. Inspired by lessons from LTCM, Niederhoffer, and
risk-of-ruin theory (Kelly criterion boundary).

Implementation note on causal integrity: The kill switch monitors the BASE
strategy's rolling drawdown (without the kill switch applied) rather than
the kill-switch-modified equity. This avoids circular feedback in the
backtest and corresponds to a conservative trigger: the base-equity drawdown
is a lower bound, so the actual portfolio's drawdown is equal-or-better
during kill periods (correct direction — we never exit when we should stay).
The approximation diverges slightly in recovery timing but is negligible for
infrequent, deep-drawdown events. Noted as an approximation in the research log.

Research basis:
- Grossman & Zhou (1993). "Optimal Investment Strategies for Controlling
  Drawdowns." Math. Finance 3(3). Drawdown constraints increase long-run
  utility for loss-averse investors.
- Cvitanić & Karatzas (1995). Portfolio optimization with drawdown constraints.
- Burgess (2004). "Using Drawdown as a Performance Metric." Risk.
- Lowenstein (2000). "When Genius Failed" (LTCM). The canonical lesson that
  leverage + no kill-switch = existential ruin even with a "correct" model.
- Skeptical prior: whipsaw cost — entering/exiting on noise adds turnover.
  Pre-registered bar requires DD improvement > 2pp net of Sharpe penalty < 0.05.

Parameters (max 2): kill_dd (float, negative — portfolio DD level to exit),
                    recovery_dd (float, negative — DD level to re-enter).
"""
import numpy as np
import pandas as pd

DEFAULTS = {"kill_dd": -0.12, "recovery_dd": -0.06}


def overlay_signals(base_signal: pd.Series, close: pd.Series,
                    kill_dd: float = -0.12, recovery_dd: float = -0.06,
                    commission: float = 0.0015) -> pd.Series:
    """Wrap a base single-asset signal with a drawdown kill-switch.

    Args:
        base_signal : Exposure series in [0, 1] from any single-asset strategy.
        close       : Corresponding price series (same index).
        kill_dd     : (negative) DD at which to exit to cash. Default -0.12.
        recovery_dd : (negative) DD at which to re-enter. Default -0.06.
        commission  : Cost per unit of turnover (for equity simulation).

    Returns:
        Modified signal series; same index as base_signal, in [0, 1].
    """
    # Simulate the base strategy's equity to compute its drawdown
    r = close.pct_change().fillna(0.0)
    pos = base_signal.clip(0.0, 1.0).shift(2).fillna(0.0)
    cost = commission * pos.diff().abs().fillna(0.0)
    base_equity = (1.0 + pos * r - cost).cumprod()
    base_dd = (base_equity / base_equity.cummax()) - 1.0

    # State machine: once kill is triggered, stay in cash until recovery
    sig_arr = base_signal.to_numpy(dtype=float).copy()
    dd_arr = base_dd.to_numpy(dtype=float)
    in_kill = False

    for i in range(len(sig_arr)):
        if in_kill:
            sig_arr[i] = 0.0
            if dd_arr[i] >= recovery_dd:
                in_kill = False
        else:
            if dd_arr[i] < kill_dd:
                in_kill = True
                sig_arr[i] = 0.0

    return pd.Series(sig_arr, index=base_signal.index, name="drawdown_kill")
