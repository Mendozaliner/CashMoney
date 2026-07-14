"""Common strategy interface.

A strategy module exposes:

    signals(close: pd.Series, **params) -> pd.Series

The returned series holds target exposure in [0, 1], indexed like `close`.
CAUSALITY CONTRACT: the value at date t may use information up to and
including date t's close only. The backtest engine executes any change of
position at the *next* bar, so no same-bar fills on the information bar.
tests/test_no_lookahead.py enforces this contract.

Max 2 tunable parameters per strategy (house rule).
"""
