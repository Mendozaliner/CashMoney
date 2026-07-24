"""s21 mark check (2026-07-24, second run of day): no new completed close vs s20.
Confirms carried mark, guardrails, live_track."""
import sys, json, pathlib
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data.loader import load_ohlcv, data_freshness
from strategies import vol_target
from backtest import guardrails as gr
from backtest import live_track

fresh = data_freshness()
print("freshness:", fresh)

spy = load_ohlcv("SPY")["Close"]
spy = spy[spy.index.date < pd.Timestamp("2026-07-24").date()]  # drop today's bar
latest_date, latest = spy.index[-1], float(spy.iloc[-1])
print("latest usable close:", latest_date.date(), latest)

portfolio = json.load(open("portfolio.json"))
units = portfolio["positions"]["SPY"]["units"]
value = units * latest
print(f"mark value: ${value:.2f} (last_mark {portfolio['last_mark']})")

spy_ret = spy.pct_change().dropna()
res = gr.run_all(portfolio, spy_returns=spy_ret, stale_days=fresh.get("stale_days", 0), peak_value=1006.52)
ok = all(c["ok"] for c in res["checks"])
for c in res["checks"]:
    print(" ", c["guardrail"], "GREEN" if c["ok"] else "NON-GREEN", c.get("detail", ""))
print("ALL GREEN" if ok else "ATTENTION")

try:
    lt = live_track.summary(portfolio, spy)
    for k, v in lt.items(): print(" lt:", k, v)
except Exception as e:
    print(" live_track error:", e)
