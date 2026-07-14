"""Session 6 (2026-07-14) experiment runner.

E6: Faber GTAA (SPY/IWM/IEF/GLD, own-SMA gating, monthly) — new sleeve candidate.
E7: Dual Momentum retry with SHY defensive harbor (E3 failed on TLT duration).
E8: Conservative kill-switch on v2 at -20%/-10% (E4 failed on tight triggers).

All experiments pre-registered BEFORE results; 12 configs total this session.
Folds: 2000-2009 / 2010-2019 / 2020-2025H; final 12 months locked (holdout).
E6 fold-1 truncated by GLD history (2004-11+); E7 fold-1 by SHY (2002-07+).
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, gtaa, dual_momentum, drawdown_kill
from research.preregister import preregister, record_outcome, trials_this_period

HOLDOUT_START = "2025-07-14"
COST = 0.0015
FOLDS = [
    ("2000-2009",   "2000-01-01", "2009-12-31"),
    ("2010-2019",   "2010-01-01", "2019-12-31"),
    ("2020-2025H",  "2020-01-01", "2025-07-11"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-11"

freshness = loader.data_freshness()
print(f"Data freshness: {freshness}")

spy_full = loader.load_ohlcv("SPY")["Close"]
spy = spy_full[spy_full.index < HOLDOUT_START]
irx = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily = (irx / 100.0) / 252.0

UNIVERSE = ["SPY", "QQQ", "DIA", "IWM", "IEF", "SHY", "GLD"]
panel_full = loader.load_universe(UNIVERSE)
panel = panel_full[panel_full.index < HOLDOUT_START]
print(f"Panel: {panel.shape}")

prior = trials_this_period()
print(f"Prior total configs registered: {prior}")

reg_e6 = preregister(
    hypothesis=("Faber GTAA (fixed 1/4 slots SPY/IWM/IEF/GLD, each gated on its own "
                "SMA at month-end, cash slot earns T-bills) delivers SPY-class "
                "risk-adjusted returns with materially lower drawdown, WITHOUT the "
                "bond-harbor failure mode that killed E3 in 2022."),
    success_criteria=("OOS (2020-2025H) deflated-Sharpe >= 0.95 for 6 trials AND "
                      "diff-vs-SPY bootstrap CI clears zero AND worst-fold MaxDD "
                      "better (shallower) than -20% AND mean WF Sharpe >= v2's 0.844."),
    grid_size=6, primary_metric="sharpe")

reg_e7 = preregister(
    hypothesis=("Dual Momentum (GEM) with SHY as the defensive harbor fixes the 2022 "
                "TLT-duration failure of E3: short-duration defensive keeps the "
                "absolute-momentum benefit in 2008/2020 without crashing in 2022."),
    success_criteria=("OOS deflated-Sharpe >= 0.95 for 4 trials AND diff-vs-SPY CI "
                      "clears zero AND worst-fold MaxDD better than -30% AND "
                      "2020-2025H fold must not repeat E3's -42.6% DD."),
    grid_size=4, primary_metric="sharpe")

reg_e8 = preregister(
    hypothesis=("A kill-switch on v2 triggered BELOW its historical DD envelope "
                "(-20% kill / -10% re-entry) fires only in GFC/COVID-class crashes "
                "and improves worst-fold MaxDD without whipsaw cost (E4's failure)."),
    success_criteria=("Worst-fold MaxDD improves by >= 2.0 pts vs v2 AND no fold "
                      "Sharpe drops by > 0.08 vs v2 AND deflated-Sharpe >= 0.95 "
                      "for 2 trials. Overlay judged vs v2, not vs SPY."),
    grid_size=2, primary_metric="max_drawdown")

print(f"Registered: E6={reg_e6.id} E7={reg_e7.id} E8={reg_e8.id}")

def single_fold_sharpes(sig, cost=COST):
    return [ve.metrics(spy.loc[a:b], sig.loc[a:b], cost, rf_daily.loc[a:b])["Sharpe"]
            for _, a, b in FOLDS]

def single_fold_metrics(sig, label, cost=COST):
    return [ve.metrics(spy.loc[a:b], sig.loc[a:b], cost, rf_daily.loc[a:b],
                       f"{label} {n}") for n, a, b in FOLDS]

def multi_fold_sharpes(weights, pan, cost=COST):
    out = []
    for _, a, b in FOLDS:
        sr = me.portfolio_returns(pan.loc[a:b], weights.loc[a:b], cost, rf_daily.loc[a:b])
        r = sr[sr.index > sr.index[0]]
        out.append(round(float(r.mean()/r.std()*np.sqrt(252)) if r.std() > 0 else 0.0, 3))
    return out

def multi_fold_metrics(weights, pan, label, cost=COST):
    return [me.metrics(pan.loc[a:b], weights.loc[a:b], cost, rf_daily.loc[a:b],
                       f"{label} {n}") for n, a, b in FOLDS]

def multi_oos_returns(weights, pan, cost=COST):
    sr = me.portfolio_returns(pan.loc[OOS_A:OOS_B], weights.loc[OOS_A:OOS_B],
                              cost, rf_daily.loc[OOS_A:OOS_B])
    return sr[sr.index > sr.index[0]]

r_spy = spy.loc[OOS_A:OOS_B].pct_change().fillna(0.0)[1:]

# Baseline v2
v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
v2_wf = single_fold_sharpes(v2)
v2_folds = single_fold_metrics(v2, "v2")
print(f"[BASELINE] v2 WF Sharpes: {v2_wf} mean={np.mean(v2_wf):.3f}")

results = {"session": "2026-07-14-s6", "data_freshness": freshness,
           "v2_baseline_wf_sharpes": v2_wf, "E6": [], "E7": [], "E8": []}

# ── E6: GTAA ──────────────────────────────────────────────────────────────────
print("\n" + "="*60 + "\nE6: Faber GTAA")
e6_configs = [{"window": w, "band": b} for w in [150, 200, 250] for b in [0.0, 0.03]]
e6_all = []
for cfg in e6_configs:
    w = gtaa.multi_signals(panel, **cfg)
    sh = multi_fold_sharpes(w, panel); e6_all.extend(sh)
    mm = multi_fold_metrics(w, panel, f"GTAA w{cfg['window']} b{cfg['band']}")
    results["E6"].append({"cfg": cfg, "wf_sharpes": sh,
                          "mean": round(float(np.mean(sh)), 3), "folds": mm})
    print(f"  w={cfg['window']} b={cfg['band']}: WF={sh} mean={np.mean(sh):.3f} "
          f"worstDD={min(f['MaxDD'] for f in mm)}")

best_e6 = max(results["E6"], key=lambda d: d["mean"])
w_e6 = gtaa.multi_signals(panel, **best_e6["cfg"])
r_e6 = multi_oos_returns(w_e6, panel)
dsr_e6 = ev.deflated_sharpe_ratio(r_e6.values, e6_all)
ci_e6 = ev.bootstrap_difference_ci(r_e6.values, r_spy.reindex(r_e6.index).values)
worst_dd_e6 = min(f["MaxDD"] for f in best_e6["folds"])
results["E6_sig"] = {"best_cfg": best_e6["cfg"], "mean_wf": best_e6["mean"],
                     "dsr": round(float(dsr_e6), 4),
                     "ci": [round(float(ci_e6.lo), 3), round(float(ci_e6.hi), 3)],
                     "clears": bool(ci_e6.clears_noise), "worst_dd": worst_dd_e6}
print(f"  BEST {best_e6['cfg']} mean={best_e6['mean']} DSR={dsr_e6:.4f} "
      f"CI=[{ci_e6.lo:.3f},{ci_e6.hi:.3f}] worstDD={worst_dd_e6}")

# ── E7: Dual Momentum w/ SHY ─────────────────────────────────────────────────
print("\n" + "="*60 + "\nE7: Dual Momentum, SHY harbor")
e7_configs = [{"lookback": lb, "skip": sk} for lb in [126, 252] for sk in [0, 21]]
e7_all = []
for cfg in e7_configs:
    w = dual_momentum.multi_signals(panel, defensive="SHY", **cfg)
    sh = multi_fold_sharpes(w, panel); e7_all.extend(sh)
    mm = multi_fold_metrics(w, panel, f"DM-SHY lb{cfg['lookback']} sk{cfg['skip']}")
    results["E7"].append({"cfg": cfg, "wf_sharpes": sh,
                          "mean": round(float(np.mean(sh)), 3), "folds": mm})
    print(f"  lb={cfg['lookback']} sk={cfg['skip']}: WF={sh} mean={np.mean(sh):.3f} "
          f"worstDD={min(f['MaxDD'] for f in mm)}")

best_e7 = max(results["E7"], key=lambda d: d["mean"])
w_e7 = dual_momentum.multi_signals(panel, defensive="SHY", **best_e7["cfg"])
r_e7 = multi_oos_returns(w_e7, panel)
dsr_e7 = ev.deflated_sharpe_ratio(r_e7.values, e7_all)
ci_e7 = ev.bootstrap_difference_ci(r_e7.values, r_spy.reindex(r_e7.index).values)
worst_dd_e7 = min(f["MaxDD"] for f in best_e7["folds"])
oos_dd_e7 = [f["MaxDD"] for f in best_e7["folds"]][2]
results["E7_sig"] = {"best_cfg": best_e7["cfg"], "mean_wf": best_e7["mean"],
                     "dsr": round(float(dsr_e7), 4),
                     "ci": [round(float(ci_e7.lo), 3), round(float(ci_e7.hi), 3)],
                     "clears": bool(ci_e7.clears_noise), "worst_dd": worst_dd_e7,
                     "oos_dd": oos_dd_e7}
print(f"  BEST {best_e7['cfg']} mean={best_e7['mean']} DSR={dsr_e7:.4f} "
      f"CI=[{ci_e7.lo:.3f},{ci_e7.hi:.3f}] worstDD={worst_dd_e7}")

# ── E8: Conservative kill-switch on v2 ───────────────────────────────────────
print("\n" + "="*60 + "\nE8: Kill-switch -20%/-10% on v2")
e8_configs = [{"kill_dd": -0.20, "recovery_dd": -0.10},
              {"kill_dd": -0.18, "recovery_dd": -0.09}]
e8_all = []
for cfg in e8_configs:
    sig = drawdown_kill.overlay_signals(v2, spy, commission=COST, **cfg)
    sh = single_fold_sharpes(sig); e8_all.extend(sh)
    mm = single_fold_metrics(sig, f"KS {cfg['kill_dd']}/{cfg['recovery_dd']}")
    n_fires = int(((sig == 0) & (v2 > 0)).sum())
    drops = [round(v - s, 3) for v, s in zip(v2_wf, sh)]
    results["E8"].append({"cfg": cfg, "wf_sharpes": sh,
                          "mean": round(float(np.mean(sh)), 3), "folds": mm,
                          "sharpe_drops_vs_v2": drops, "days_killed": n_fires})
    print(f"  {cfg}: WF={sh} drops_vs_v2={drops} days_killed={n_fires} "
          f"worstDD={min(f['MaxDD'] for f in mm)}")

best_e8 = max(results["E8"], key=lambda d: d["mean"])
sig_e8 = drawdown_kill.overlay_signals(v2, spy, commission=COST, **best_e8["cfg"])
r_e8 = ve.strategy_returns(spy, sig_e8, COST, rf_daily).loc[OOS_A:OOS_B]
dsr_e8 = ev.deflated_sharpe_ratio(r_e8.values, e8_all)
worst_dd_e8 = min(f["MaxDD"] for f in best_e8["folds"])
worst_dd_v2 = min(f["MaxDD"] for f in v2_folds)
dd_improve = worst_dd_e8 - worst_dd_v2
max_drop = max(best_e8["sharpe_drops_vs_v2"])
results["E8_sig"] = {"best_cfg": best_e8["cfg"], "dsr": round(float(dsr_e8), 4),
                     "worst_dd": worst_dd_e8, "v2_worst_dd": worst_dd_v2,
                     "dd_improvement_pts": round(dd_improve, 2),
                     "max_fold_sharpe_drop": max_drop}
print(f"  BEST {best_e8['cfg']} DSR={dsr_e8:.4f} worstDD={worst_dd_e8} "
      f"(v2 {worst_dd_v2}) improve={dd_improve:.2f}pts maxdrop={max_drop}")

json.dump(results, open("research/results_2026_07_14_s6.json", "w"), indent=1)
print("\nSaved research/results_2026_07_14_s6.json")
