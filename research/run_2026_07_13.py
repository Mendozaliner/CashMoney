"""Session 2026-07-13: SMA trend filter grid search.

In-sample 2010-2019 (parameter selection, robustness-weighted),
out-of-sample 2020->end of data. Signals are computed on the full history
(so the SMA warmup uses only pre-period data, which was available at
decision time), then each evaluation window is sliced.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd

from data.loader import load_spy_proxy
from strategies import sma_trend
from backtest import engine

IS = ("2010-01-01", "2019-12-31")
OOS = ("2020-01-01", None)

px = load_spy_proxy()["Close"]

def eval_cfg(window, band, period):
    sig = sma_trend.signals(px, window=window, band=band)
    lo, hi = period
    c = px.loc[lo:hi]; s = sig.loc[lo:hi]
    m = engine.metrics(c, s, label=f"SMA{window}/b{band:.0%}")
    m.update(window=window, band=band)
    return m

rows = []
for w in (50, 100, 150, 200, 250, 300):
    for b in (0.0, 0.01, 0.02, 0.03):
        rows.append(eval_cfg(w, b, IS))
df = pd.DataFrame(rows)

# benchmark in-sample
bh_is = engine.metrics(px.loc[IS[0]:IS[1]],
                       engine.buy_and_hold_signal(px.loc[IS[0]:IS[1]]),
                       label="SPY B&H")
print("=== IN-SAMPLE 2010-2019 ===")
print(df[["label","CAGR","Sharpe","Sortino","MaxDD","Trades/yr"]].to_string(index=False))
print("B&H:", bh_is)

# robustness: mean Sharpe of parameter neighborhood (same window +-50, band +-0.01)
def neigh_sharpe(r):
    m = df[(df.window.sub(r.window).abs() <= 50) & (df.band.sub(r.band).abs() <= 0.011)]
    return m.Sharpe.mean()
df["NeighSharpe"] = df.apply(neigh_sharpe, axis=1)
best = df.sort_values(["NeighSharpe", "Sharpe"], ascending=False).iloc[0]
print("\nChampion by robustness-weighted IS Sharpe:", best.label,
      "IS Sharpe", best.Sharpe, "neigh", round(best.NeighSharpe, 3))

df.to_csv("research/results_2026_07_13_insample.csv", index=False)

print("\n=== OUT-OF-SAMPLE 2020-present ===")
oos_rows = [eval_cfg(int(best.window), float(best.band), OOS)]
bh_oos = engine.metrics(px.loc[OOS[0]:], engine.buy_and_hold_signal(px.loc[OOS[0]:]), label="SPY B&H")
oos_rows.append(bh_oos)
# also show faber classic 200/0 for reference
oos_rows.append(eval_cfg(200, 0.0, OOS))
oos = pd.DataFrame(oos_rows)
print(oos[["label","CAGR","Sharpe","Sortino","MaxDD","WinRate","Trades/yr","End$per1k"]].to_string(index=False))
oos.to_csv("research/results_2026_07_13_oos.csv", index=False)

print("\n=== TRAILING 12 MONTHS, $1,000 start ===")
end = px.index[-1]; start = end - pd.DateOffset(months=12)
t12 = (str(start.date()), None)
r1 = eval_cfg(int(best.window), float(best.band), t12)
r2 = engine.metrics(px.loc[t12[0]:], engine.buy_and_hold_signal(px.loc[t12[0]:]), label="SPY B&H")
print(f"window {start.date()} -> {end.date()}")
print(pd.DataFrame([r1, r2])[["label","End$per1k","MaxDD","Trades"]].to_string(index=False))
