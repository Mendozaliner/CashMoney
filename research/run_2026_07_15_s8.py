"""Session 8 (2026-07-15) experiment runner.

E12: Trend-gated naive risk parity on SPY/IEF/GLD (roadmap item #5).
M2:  Correlation memo — E12 best config vs frozen champion v2 (ensemble check).

Pre-registered BEFORE results. 6 configs. Walk-forward folds:
2000-2009 / 2010-2019 / 2020-2025H; final 12 months locked (holdout).
Fold-1 truncated by IEF (2002-07) and GLD (2004-11) listings — slots with no
history sit in cash by construction; flagged, per the GTAA E6/E10 convention.
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, risk_parity as rp
from research.preregister import preregister, record_outcome, trials_this_period

HOLDOUT_START = "2025-07-14"
COST = 0.0015
FOLDS = [
    ("2000-2009",  "2000-01-01", "2009-12-31"),
    ("2010-2019",  "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-11"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-11"

print("freshness:", loader.data_freshness())
prior = trials_this_period()
print("prior registered configs:", prior)

panel = loader.load_universe(["SPY", "IEF", "GLD"])
panel = panel[panel.index < HOLDOUT_START]
spy = panel["SPY"].dropna()
irx = loader.load_ohlcv("^IRX")["Close"].reindex(panel.index).ffill()
rf_daily = (irx / 100.0) / 252.0

reg = preregister(
    hypothesis=(
        "Trend-gated naive risk parity (inverse-vol slots over SPY/IEF/GLD, SMA200 "
        "gate per asset, excluded slots to T-bills) improves risk-adjusted returns vs "
        "v2 by sizing across genuinely different asset classes by risk rather than "
        "concentrating in equity. The per-asset trend gate specifically counters the "
        "2022 RP failure mode (bond overweight when stock/bond correlation flips). "
        "Skeptical prior: unlevered RP lags SPY on raw return (Asness 2012; arXiv "
        "1307.0114); expect a GTAA-like outcome — good DD, insufficient significance."
    ),
    success_criteria=(
        "OOS (2020-2025H) deflated-Sharpe >= 0.95 across all trials this idea AND "
        "diff-vs-SPY bootstrap CI lower bound > 0 AND worst-fold MaxDD shallower than "
        "-20% AND mean WF Sharpe >= v2's 0.844. Fold-1 is truncated (IEF 2002-07, "
        "GLD 2004-11): flagged, weighted per the E10 convention (fold-2/3 emphasis), "
        "but the bars above are unchanged."
    ),
    grid_size=6, primary_metric="sharpe")
print("registered:", reg.id)

GRID = [(lb, band) for lb in (20, 60, 120) for band in (0.0, 0.03)]
rows, oos_rets, trial_sharpes = [], {}, []
for lb, band in GRID:
    w = rp.multi_signals(panel, lookback=lb, band=band)
    label = f"RP lb{lb}/b{band:g}"
    fold_sh = []
    worst_dd = 0.0
    for name, a, b in FOLDS:
        pw = w.loc[a:b]; pp = panel.loc[a:b]
        m = me.metrics(pp, pw, commission=COST, rf_daily=rf_daily.loc[a:b], label=label)
        fold_sh.append(m["Sharpe"]); worst_dd = min(worst_dd, m["MaxDD"])
    r_oos = me.portfolio_returns(panel.loc[OOS_A:OOS_B], w.loc[OOS_A:OOS_B],
                                 commission=COST, rf_daily=rf_daily.loc[OOS_A:OOS_B])
    oos_sh = ev.sharpe_ratio(r_oos)
    trial_sharpes.append(oos_sh)
    oos_rets[label] = r_oos
    rows.append({"label": label, "folds": [round(s,3) for s in fold_sh],
                 "meanWF": round(float(np.mean(fold_sh)),3),
                 "worstDD": round(worst_dd,2), "oos_sharpe": round(float(oos_sh),3)})
    print(rows[-1])

best = max(rows, key=lambda r: r["meanWF"])
print("BEST:", best)
r_best = oos_rets[best["label"]]

spy_oos = spy.loc[OOS_A:OOS_B]
spy_ret = spy_oos.pct_change().dropna()
r_best_al, spy_al = r_best.align(spy_ret, join="inner")

dsr = ev.deflated_sharpe_ratio(r_best_al, trial_sharpes)
ci = ev.bootstrap_difference_ci(r_best_al, spy_al)
print(f"DSR={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise}")

# M2: correlation with frozen v2 (OOS window)
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST,
                           rf_daily=rf_daily.reindex(spy.index).fillna(0.0))
r_v2_oos = r_v2.loc[OOS_A:OOS_B]
a1, a2 = r_best.align(r_v2_oos, join="inner")
corr = float(a1.corr(a2))

# $1k full-sample comparison (2004-11 GLD start caveat) + ensemble sketch
w_best = rp.multi_signals(panel, lookback=int(best["label"].split("lb")[1].split("/")[0]),
                          band=float(best["label"].split("/b")[1]))
r_full = me.portfolio_returns(panel, w_best, commission=COST, rf_daily=rf_daily)
r_v2_full = r_v2.reindex(r_full.index).fillna(0.0)
end_rp   = float((1+r_full).prod()*1000)
end_v2   = float((1+r_v2.loc[r_full.index[0]:]).prod()*1000)
end_spy  = float((1+spy.pct_change().loc[r_full.index[0]:].fillna(0)).prod()*1000)
r_ens = 0.5*r_full + 0.5*r_v2_full
end_ens = float((1+r_ens).prod()*1000)
ens_oos = 0.5*a1 + 0.5*a2
ens_sh = ev.sharpe_ratio(ens_oos)
print(f"M2: corr(RP,v2) OOS = {corr:.3f}; ens OOS Sharpe {ens_sh:.3f}")
print(f"$1k 2000->: RP {end_rp:.0f}  v2 {end_v2:.0f}  SPY {end_spy:.0f}  50/50 {end_ens:.0f}")

verdict_pass = (dsr >= 0.95 and ci.lo > 0 and best["worstDD"] > -20
                and best["meanWF"] >= 0.844)
verdict = "adopted" if verdict_pass else "discarded"
evidence = {"best": best, "dsr": round(float(dsr),4),
            "diff_ci": [round(ci.lo,3), round(ci.hi,3)],
            "corr_v2_oos": round(corr,3), "ens_oos_sharpe": round(float(ens_sh),3),
            "end1k": {"rp": round(end_rp,2), "v2": round(end_v2,2),
                      "spy": round(end_spy,2), "ens5050": round(end_ens,2)},
            "all_rows": rows}
record_outcome(reg.id, verdict=verdict, evidence=evidence)
print("VERDICT:", verdict)

json.dump(evidence, open("research/results_2026_07_15_s8.json","w"), indent=1)
print("total registered configs now:", trials_this_period())
