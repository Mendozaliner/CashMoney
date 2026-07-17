"""Session 11 (2026-07-17): E17 RSI-2, E18 Bollinger, E19 IBS mean reversion.

Last unexplored charter-queue family, run as a candidate NEW SLEEVE.
Data fresh through 2026-07-16. Holdout locked from 2025-07-17.
"""
import sys, json
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data import loader
from backtest import vector_engine as ve, evaluation as ev
from strategies import vol_target, mean_reversion as mr
from research.preregister import preregister, record_outcome, trials_this_period

HOLDOUT_START = "2025-07-17"   # locked 12-month holdout
COST = 0.0015
FOLDS = [
    ("2000-2009", "2000-01-01", "2009-12-31"),
    ("2010-2019", "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-16"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-16"

ohlc_full = loader.load_ohlcv("SPY")
ohlc = ohlc_full[ohlc_full.index < HOLDOUT_START].copy()
spy = ohlc["Close"]
irx = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily = (irx / 100.0) / 252.0
spy_ret = spy.pct_change().fillna(0.0)

sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily)

print(f"Data through {spy.index[-1].date()}  SPY {spy.iloc[-1]:.2f}")
print(f"Registered configs before session: {trials_this_period()}")

def wf_metrics(r, label=""):
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        x = r.loc[a:b]
        if len(x) < 60:
            fold_sharpes.append(0.0); continue
        fold_sharpes.append(round(ev.sharpe_ratio(x), 3))
        eq = (1 + x).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    oos = r.loc[OOS_A:OOS_B]
    return {"label": label, "folds": fold_sharpes,
            "mean_wf": round(float(np.mean(fold_sharpes)), 3),
            "worst_dd": round(worst_dd * 100, 2),
            "oos_sharpe": round(ev.sharpe_ratio(oos), 3),
            "end1k": round(float((1 + r).prod() * 1000), 2)}

def significance(r, trial_sharpes, label):
    oos = r.loc[OOS_A:OOS_B]
    b = spy_ret.reindex(oos.index).fillna(0.0)
    dsr = ev.deflated_sharpe_ratio(oos, trial_sharpes)
    ci = ev.bootstrap_difference_ci(oos, b)
    print(f"  {label}: DSR={dsr:.4f} diff-CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise}")
    return dsr, ci

BAR = ("Adoptable as new MR-sleeve champion ONLY IF mean WF Sharpe >= 0.844 "
       "AND worst-fold MaxDD shallower than -20% AND DSR >= 0.95 AND OOS "
       "diff-vs-SPY CI clears zero. Primary metric: mean WF Sharpe.")
results = {}
all_trial_sharpes = []

# E17 RSI-2 -----------------------------------------------------------------
reg17 = preregister(
    hypothesis=("Connors RSI(2) buy-the-dip on SPY, SMA200-gated, EOD "
                "next-close fills, survives realistic 0.15% costs and beats "
                "SPY risk-adjusted out-of-sample. Skeptical prior: Price "
                "Action Lab says the edge is a data-mined artifact."),
    success_criteria=BAR, grid_size=6, primary_metric="mean_wf_sharpe")
grid17 = [(e, x) for e in (5.0, 10.0, 15.0) for x in (70.0, 80.0)]
rows = []
for e, x in grid17:
    r = ve.strategy_returns(spy, mr.rsi2_signals(spy, e, x), COST, rf_daily)
    m = wf_metrics(r, f"RSI2(e{e:.0f},x{x:.0f})")
    m["ann_sharpe_full"] = round(ev.sharpe_ratio(r), 3)
    rows.append((m, r))
    all_trial_sharpes.append(m["ann_sharpe_full"])
    print(m)
best17, r17 = max(rows, key=lambda t: t[0]["mean_wf"])
results["E17"] = best17

# E18 Bollinger -------------------------------------------------------------
reg18 = preregister(
    hypothesis=("Bollinger(20,k) lower-band mean reversion on SPY, SMA200-"
                "gated, exit at middle band, survives 0.15% costs and beats "
                "SPY risk-adjusted OOS. Literature: in-sample-pretty, "
                "cost-fragile."),
    success_criteria=BAR, grid_size=4, primary_metric="mean_wf_sharpe")
grid18 = [(k, xa) for k in (2.0, 2.5) for xa in ("mid", "upper_half")]
rows = []
for k, xa in grid18:
    r = ve.strategy_returns(spy, mr.bollinger_signals(spy, k, xa), COST, rf_daily)
    m = wf_metrics(r, f"BB(k{k},{xa})")
    m["ann_sharpe_full"] = round(ev.sharpe_ratio(r), 3)
    rows.append((m, r)); all_trial_sharpes.append(m["ann_sharpe_full"])
    print(m)
best18, r18 = max(rows, key=lambda t: t[0]["mean_wf"])
results["E18"] = best18

# E19 IBS -------------------------------------------------------------------
reg19 = preregister(
    hypothesis=("Pagonidis IBS(<0.2 in, >0.8 out) on SPY, SMA200-gated, "
                "survives 0.15% costs at EOD next-close fills and beats SPY "
                "risk-adjusted OOS. Prior: replications mixed, cost-fragile, "
                "and next-close fill gives away most of the overnight edge."),
    success_criteria=BAR, grid_size=4, primary_metric="mean_wf_sharpe")
grid19 = [(e, x) for e in (0.1, 0.2) for x in (0.7, 0.8)]
rows = []
for e, x in grid19:
    r = ve.strategy_returns(spy, mr.ibs_signals(ohlc, e, x), COST, rf_daily)
    m = wf_metrics(r, f"IBS(e{e},x{x})")
    m["ann_sharpe_full"] = round(ev.sharpe_ratio(r), 3)
    rows.append((m, r)); all_trial_sharpes.append(m["ann_sharpe_full"])
    print(m)
best19, r19 = max(rows, key=lambda t: t[0]["mean_wf"])
results["E19"] = best19

# Benchmarks + significance --------------------------------------------------
print("\nBenchmarks:")
print(wf_metrics(spy_ret, "SPY B&H"))
print(wf_metrics(r_v2, "v2 champion"))

print("\nSignificance (vs SPY OOS, deflated across the 14-config session grid):")
d17, c17 = significance(r17, all_trial_sharpes, best17["label"])
d18, c18 = significance(r18, all_trial_sharpes, best18["label"])
d19, c19 = significance(r19, all_trial_sharpes, best19["label"])

# correlation of best configs with v2 (daily, OOS)
for nm, rr in (("E17", r17), ("E18", r18), ("E19", r19)):
    a, b = rr.loc[OOS_A:OOS_B].align(r_v2.loc[OOS_A:OOS_B], join="inner")
    print(f"corr({nm}, v2) OOS: {a.corr(b):.3f}")

for reg, best, d, c in ((reg17, best17, d17, c17), (reg18, best18, d18, c18),
                        (reg19, best19, d19, c19)):
    passed = (best["mean_wf"] >= 0.844 and best["worst_dd"] > -20.0
              and d >= 0.95 and c.clears_noise)
    record_outcome(reg.id,
                   "adopted" if passed else "discarded",
                   {"best": best, "dsr": round(float(d), 4),
                    "ci": [round(c.lo, 3), round(c.hi, 3)]})
    print(best["label"], "->", "adopted" if passed else "discarded")

json.dump(results, open("research/results_2026_07_17.json", "w"), indent=1)
print("\nRegistered configs after session:", trials_this_period())
