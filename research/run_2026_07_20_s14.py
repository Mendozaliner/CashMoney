"""Session 14 (2026-07-20, second run today) — maintenance + standing items.

NOTE: benchmark-panel $1k figures are computed on the sample CUT AT THE LOCKED
HOLDOUT START (2025-07-17), matching every prior session's published numbers.
The first draft of this script accidentally included the holdout window; the
corrected figures (v2 $8,381.85 from 2000, matching s13) are in the memo
research/2026-07-20-s14-benchmark-panel.md.

No new configs, no new experiments (research queue exhausted per ROADMAP).
Work: (a) freshness + mark verification, (b) guardrails, (c) STANDING
benchmark panel incl. international indexes per Mr. Menendez's instruction,
(d) after-tax do-nothing verdict, (e) full test suite.
"""
import sys, json
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from data import loader
from strategies import vol_target
from backtest import vector_engine as ve
from backtest import guardrails
from backtest.evaluation import do_nothing_verdict

TODAY = pd.Timestamp("2026-07-20")

# ---------- freshness ----------
f = loader.data_freshness()
print("FRESHNESS:", json.dumps(f, default=str))
newest = pd.Timestamp(f["newest_close"])
# trading-day staleness: business days strictly between newest close and today
bdays_missed = len(pd.bdate_range(newest + pd.Timedelta(days=1),
                                  TODAY - pd.Timedelta(days=1)))
print(f"Business days missed between {newest.date()} and today (exclusive): {bdays_missed}")

# ---------- champion exposure + mark ----------
spy = loader.load_ohlcv("SPY")["Close"]
spy = spy[spy.index < TODAY]           # drop any current-day bar
irx = loader.load_ohlcv("^IRX")["Close"]
rf_daily = (irx.reindex(spy.index).ffill() / 100.0) / 252.0

sig = vol_target.signals(spy, target_vol=0.18, lookback=20)
last_close = float(spy.iloc[-1]); last_date = spy.index[-1]
sma200 = spy.rolling(200).mean().iloc[-1] * 1.03
vol20 = float(spy.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252))
expo = float(sig.iloc[-1])
UNITS = 1.3334757435413753
mark = UNITS * last_close
print(f"MARK: {last_date.date()} SPY {last_close:.2f} -> ${mark:.2f}; "
      f"exposure {expo:.3f} (band {sma200:.2f}, 20d vol {vol20:.1%})")

# live window vs SPY (baseline 2026-07-13 @ 749.17, carried $999.00)
spy_live = float(last_close / 749.1699829101562 - 1)
port_live_alltime = mark / 1000 - 1
print(f"LIVE: all-time {port_live_alltime:+.3%} vs SPY since baseline {spy_live:+.3%}")
peak = 1006.52
print(f"Drawdown from peak ${peak}: {mark/peak-1:+.3%}")

# ---------- guardrails ----------
portfolio = json.load(open("portfolio.json"))
spy_rets = spy.pct_change().dropna()
res = guardrails.run_all(portfolio, spy_returns=spy_rets, stale_days=bdays_missed)
print("GUARDRAILS:", res)

# ---------- benchmark panel (standing instruction) ----------
def bh_stats(px, start):
    px = px[px.index >= start].dropna()
    if len(px) < 50: return None
    eq = px / px.iloc[0]
    yrs = (px.index[-1] - px.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return {"end$": round(1000 * float(eq.iloc[-1]), 0),
            "cagr%": round(100 * float(cagr), 1),
            "worstDD%": round(100 * float(dd), 1)}

def v2_stats(start):
    m = ve.metrics(spy[spy.index >= start],
                   sig[sig.index >= start], commission=0.0015,
                   rf_daily=rf_daily, label="v2")
    return {"end$": m["End$per1k"], "cagr%": m["CAGR"], "worstDD%": m["MaxDD"]}

panel_tickers = ["SPY", "QQQ", "DIA", "EWC", "ACWI", "^GSPTSE", "^FTSE",
                 "^N225", "^GDAXI", "^HSI"]
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

panel = {}
CUT = pd.Timestamp("2025-07-17")  # locked holdout start — never inspected for tuning
spy_p = spy[spy.index < CUT]; sig_p = sig[sig.index < CUT]
for start_lbl, start in [("2000", "2000-01-03"), ("2010", "2010-01-04"),
                         ("2020", "2020-01-02")]:
    row = {"v2": {"end$": ve.metrics(spy_p[spy_p.index >= start], sig_p[sig_p.index >= start], commission=0.0015, rf_daily=rf_daily, label="v2")["End$per1k"]}}
    for t in panel_tickers:
        try:
            px = loader.load_ohlcv(t)["Close"]
            px = px[px.index < CUT]
            row[t] = bh_stats(px, start)
        except Exception as e:
            row[t] = f"ERR {e}"
    # Mag-7 equal weight (daily rebalanced, common history only)
    m7 = loader.load_universe(mag7)
    m7 = m7[m7.index < CUT].dropna()
    m7r = m7.pct_change().mean(axis=1)
    m7r = m7r[m7r.index >= start]
    eq = (1 + m7r).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    row["Mag7eqw*"] = {"end$": round(1000 * float(eq.iloc[-1]), 0),
                       "cagr%": round(100 * (float(eq.iloc[-1]) ** (1/yrs) - 1), 1),
                       "worstDD%": round(100 * float((eq/eq.cummax()-1).min()), 1),
                       "from": str(eq.index[0].date())}
    panel[start_lbl] = row

print("PANEL:")
for lbl, row in panel.items():
    print(f"--- from {lbl} ---")
    for k, v in row.items():
        print(f"  {k}: {v}")

# ---------- after-tax do-nothing verdict (2020 -> 2025-06-30) ----------
w0, w1 = "2020-01-02", "2025-06-30"
sr = ve.strategy_returns(spy, sig, commission=0.0015, rf_daily=rf_daily)
sr_w = sr[(sr.index >= w0) & (sr.index <= w1)]
pos = sig.clip(0, 1).shift(2).fillna(0.0).reindex(sr_w.index)
# segment risk-on blocks (exposure > 0) into "trades"
on = pos > 1e-9
blocks, cur = [], None
for dt, flag in on.items():
    if flag and cur is None: cur = [dt, dt]
    elif flag: cur[1] = dt
    elif cur is not None: blocks.append(cur); cur = None
if cur is not None: blocks.append(cur)
trade_rets, hold_days = [], []
for a, b in blocks:
    seg = sr_w[(sr_w.index >= a) & (sr_w.index <= b)]
    trade_rets.append(float(np.prod(1 + seg) - 1))
    hold_days.append((b - a).days + 1)
spy_w = spy[(spy.index >= w0) & (spy.index <= w1)].pct_change().dropna()
v = do_nothing_verdict(trade_rets, hold_days, spy_w.values)
print("DO-NOTHING (2020->2025H):", str(v))
print(f"  trades={len(trade_rets)}, holding days={hold_days}")
