"""Session 8b (2026-07-15): E13 — v2 + trend-gated risk parity ensemble.

Trigger: roadmap item #2 revisit condition MET — E12 corr(RP,v2)=0.467 < 0.50
(GTAA was 0.721, blocked). Testing whether combining two weakly-correlated
sleeves lifts significance vs SPY where each alone fails.
3 configs: v2 weight {0.3, 0.5, 0.7}, remainder in RP(lb60, b0.03).
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
FOLDS = [("2000-2009","2000-01-01","2009-12-31"),
         ("2010-2019","2010-01-01","2019-12-31"),
         ("2020-2025H","2020-01-01","2025-07-11")]
OOS_A, OOS_B = "2020-01-01", "2025-07-11"

panel = loader.load_universe(["SPY","IEF","GLD"])
panel = panel[panel.index < HOLDOUT_START]
spy = panel["SPY"].dropna()
irx = loader.load_ohlcv("^IRX")["Close"].reindex(panel.index).ffill()
rf_daily = (irx/100.0)/252.0

reg = preregister(
    hypothesis=(
        "A fixed-mix ensemble of frozen champion v2 (trend-gated vol-target SPY) and "
        "E12's trend-gated risk parity (SPY/IEF/GLD, lb60/b0.03) exploits their low "
        "correlation (0.467 OOS) to clear the significance gate that each sleeve "
        "fails alone: diversification should shrink the variance of the strategy-"
        "minus-SPY difference more than it shrinks its mean. This is the roadmap's "
        "stated path (cross-strategy diversification over more single-strategy tuning)."
    ),
    success_criteria=(
        "OOS deflated-Sharpe >= 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0 AND "
        "worst-fold MaxDD shallower than -20% AND mean WF Sharpe >= v2's 0.844 AND "
        "full-sample $1k terminal >= SPY buy-and-hold's over the same window (no raw-"
        "return giveaway like the GTAA 50/50, which was rejected at $6,542 vs $9,258)."
    ),
    grid_size=3, primary_metric="sharpe")
print("registered:", reg.id)

# Sleeve returns (full sample on RP's valid index)
w_rp = rp.multi_signals(panel, lookback=60, band=0.03)
r_rp = me.portfolio_returns(panel, w_rp, commission=COST, rf_daily=rf_daily)
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST,
                           rf_daily=rf_daily.reindex(spy.index).fillna(0.0))
r_v2 = r_v2.reindex(r_rp.index).fillna(0.0)
spy_ret = spy.pct_change().reindex(r_rp.index).fillna(0.0)

def perf(r, a, b):
    x = r.loc[a:b]
    sh = ev.sharpe_ratio(x)
    eq = (1+x).cumprod()
    dd = float((eq/eq.cummax()-1).min())
    return sh, dd

rows, trial_sharpes, oos_rets = [], [], {}
for wv in (0.3, 0.5, 0.7):
    r_mix = wv*r_v2 + (1-wv)*r_rp
    label = f"ENS v2:{wv:.0%}/RP:{1-wv:.0%}"
    folds, worst = [], 0.0
    for name, a, b in FOLDS:
        sh, dd = perf(r_mix, a, b); folds.append(round(sh,3)); worst = min(worst, dd)
    oos = r_mix.loc[OOS_A:OOS_B]
    trial_sharpes.append(ev.sharpe_ratio(oos)); oos_rets[label] = oos
    end1k = float((1+r_mix).prod()*1000)
    rows.append({"label":label,"folds":folds,"meanWF":round(float(np.mean(folds)),3),
                 "worstDD":round(worst*100,2),"oos_sharpe":round(trial_sharpes[-1],3),
                 "end1k":round(end1k,2)})
    print(rows[-1])

end_spy = float((1+spy_ret).prod()*1000)
end_v2  = float((1+r_v2).prod()*1000)
print(f"$1k same window: SPY {end_spy:.0f}  v2 {end_v2:.0f}")

best = max(rows, key=lambda r: r["meanWF"])
r_best = oos_rets[best["label"]]
spy_oos = spy.pct_change().loc[OOS_A:OOS_B].dropna()
a1, a2 = r_best.align(spy_oos, join="inner")
# Deflate across ALL trials burned on this family this session (E12's 6 + these 3)
all_trials = trial_sharpes + [0.731,1.282,0.75,1.291,0.768,1.302]
dsr = ev.deflated_sharpe_ratio(a1, all_trials)
ci = ev.bootstrap_difference_ci(a1, a2)
print("BEST:", best)
print(f"DSR(9 trials)={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise}")

ok = (dsr>=0.95 and ci.lo>0 and best["worstDD"]>-20 and best["meanWF"]>=0.844
      and best["end1k"]>=end_spy)
verdict = "adopted" if ok else "discarded"
evidence = {"best":best,"dsr":round(float(dsr),4),"diff_ci":[round(ci.lo,3),round(ci.hi,3)],
            "end1k_spy":round(end_spy,2),"end1k_v2":round(end_v2,2),"all_rows":rows}
record_outcome(reg.id, verdict=verdict, evidence=evidence)
print("VERDICT:", verdict)
json.dump(evidence, open("research/results_2026_07_15_s8b.json","w"), indent=1)
print("total configs:", trials_this_period())
