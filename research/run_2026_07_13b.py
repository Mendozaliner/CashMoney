"""Session 2 experiments: E1 rf cash yield, E2 vol-target overlay, E3 both.

IS 2010-2019 for parameter selection (neighborhood-average Sharpe);
OOS 2020 -> end. Signals computed on full history, then sliced."""
import itertools
import numpy as np
import pandas as pd

from backtest import vector_engine as ve
from data.loader import load_spy_proxy
from strategies import sma_trend, vol_target

d = load_spy_proxy()
d = d[d.index < pd.Timestamp.now().normalize()]  # drop incomplete current day
close, rf_idx = d["Close"], d["RiskFreeIndex"]
rf_daily = rf_idx.pct_change().fillna(0.0)

IS, OOS = slice("2010-01-01", "2019-12-31"), slice("2020-01-01", None)
champ_sig = sma_trend.signals(close, 200, 0.03)
bh = pd.Series(1.0, index=close.index)


def m(sig, period, rf=None, label=""):
    c = close.loc[period]
    return ve.metrics(c, sig.loc[period], rf_daily=(rf.loc[period] if rf is not None else None), label=label)

rows = []
for period, tag in [(IS, "IS"), (OOS, "OOS")]:
    rows.append(m(bh, period, label=f"{tag} SPY B&H"))
    rows.append(m(champ_sig, period, label=f"{tag} champion SMA200/b3"))
    rows.append(m(champ_sig, period, rf=rf_daily, label=f"{tag} E1 champ+rfcash"))

# E2 grid, in-sample only
tvs = [0.10, 0.12, 0.15, 0.18]
lbs = [20, 40, 60]
grid = {}
for tv, lb in itertools.product(tvs, lbs):
    sig = vol_target.signals(close, tv, lb)
    grid[(tv, lb)] = ve.metrics(close.loc[IS], sig.loc[IS],
                                label=f"IS E2 vt{tv}/lb{lb}")
gdf = pd.DataFrame(grid.values(), index=pd.MultiIndex.from_tuples(grid.keys(), names=["tv", "lb"]))

# neighborhood-average Sharpe (adjacent cells in the grid incl. self)
def neigh_sharpe(tv, lb):
    ti, li = tvs.index(tv), lbs.index(lb)
    vals = []
    for dt, dl in itertools.product([-1, 0, 1], repeat=2):
        t2, l2 = ti + dt, li + dl
        if 0 <= t2 < len(tvs) and 0 <= l2 < len(lbs):
            vals.append(grid[(tvs[t2], lbs[l2])]["Sharpe"])
    return np.mean(vals)

gdf["NeighSharpe"] = [neigh_sharpe(tv, lb) for tv, lb in gdf.index]
best_tv, best_lb = gdf["NeighSharpe"].idxmax()
print("IS grid:\n", gdf[["Sharpe", "MaxDD", "Turnover/yr", "AvgExposure", "NeighSharpe"]].round(3))
print(f"\nSelected by neighborhood Sharpe: tv={best_tv}, lb={best_lb}")

sig2 = vol_target.signals(close, best_tv, best_lb)
rows.append(m(sig2, IS, label=f"IS E2 vt{best_tv}/lb{best_lb}"))
rows.append(m(sig2, OOS, label=f"OOS E2 vt{best_tv}/lb{best_lb}"))
rows.append(m(sig2, OOS, rf=rf_daily, label=f"OOS E3 E2+rfcash"))
# OOS robustness: parameter neighbors of the selection
for tv, lb in [(best_tv, lbs[max(0, lbs.index(best_lb)-1)]),
               (best_tv, lbs[min(len(lbs)-1, lbs.index(best_lb)+1)]),
               (tvs[max(0, tvs.index(best_tv)-1)], best_lb),
               (tvs[min(len(tvs)-1, tvs.index(best_tv)+1)], best_lb)]:
    if (tv, lb) != (best_tv, best_lb):
        rows.append(m(vol_target.signals(close, tv, lb), OOS,
                      label=f"OOS E2nbr vt{tv}/lb{lb}"))

res = pd.DataFrame(rows)
print("\n", res.to_string(index=False))
res.to_csv("research/results_2026_07_13b.csv", index=False)
gdf.reset_index().to_csv("research/results_2026_07_13b_grid_is.csv", index=False)
