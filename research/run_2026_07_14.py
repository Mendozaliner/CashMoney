"""Session 2026-07-14: first experiments on the REAL data pipeline.

E1 (roadmap #1): wider vol-target grid -- is champion v2's tv=0.18 a plateau
   or a grid-edge artifact?  tv {0.21,0.24,0.27,0.30} x lb {20,60,120}.
E2 (roadmap #2): VIX-percentile de-risking overlay on frozen v2 (Phase-2
   risk-overlay lane). Skeptical prior: literature says high VIX tends to
   PRECEDE high returns (QuantPedia high-VIX threshold; MDPI VIX-futures
   timing; Hartford "when fear runs high"), so expect failure.

Protocol: SPY 2000-01-03 -> holdout start; LOCKED FINAL HOLDOUT = last 12
months (2025-07-14 onward) untouched. Walk-forward folds 2000-09 / 2010-19 /
2020-25. Costs 0.15% per unit turnover (0.1% commission + 0.05% slippage --
the END-GOAL bar; prior sessions used 0.10%, both shown for the champion).
"""
import sys, json; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from data import loader
from backtest import vector_engine as ve, evaluation as ev
from strategies import vol_target, sma_trend

HOLDOUT_START = "2025-07-14"          # locked; never inspected here
COST = 0.0015
FOLDS = [("2000-2009", "2000-01-01", "2009-12-31"),
         ("2010-2019", "2010-01-01", "2019-12-31"),
         ("2020-2025H", "2020-01-01", "2025-07-11")]

spy_full = loader.load_ohlcv("SPY")["Close"]
spy = spy_full[spy_full.index < HOLDOUT_START]
vix = loader.load_ohlcv("^VIX")["Close"].reindex(spy.index).ffill()
irx = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily = (irx / 100.0) / 252.0      # 13w discount yield approx daily accrual

def fold_metrics(sig, label, cost=COST):
    rows = []
    for name, a, b in FOLDS:
        m = ve.metrics(spy.loc[a:b], sig.loc[a:b], cost, rf_daily.loc[a:b], f"{label} {name}")
        rows.append(m)
    return rows

def wf_sharpes(sig, cost=COST):
    return [ve.metrics(spy.loc[a:b], sig.loc[a:b], cost, rf_daily.loc[a:b])["Sharpe"]
            for _, a, b in FOLDS]

def rets(sig, a, b, cost=COST):
    return ve.strategy_returns(spy, sig, cost, rf_daily).loc[a:b]

# ---------------- baselines on REAL data ----------------
one = pd.Series(1.0, index=spy.index)
v1 = sma_trend.signals(spy, window=200, band=0.03)
v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)

out = {"baselines": {}, "E1": [], "E2": []}
for lbl, sig in [("SPY B&H", one), ("v1 sma200/b3", v1), ("v2 vt18/lb20", v2)]:
    out["baselines"][lbl] = fold_metrics(sig, lbl)
# champion also at the old 0.10% cost for continuity
out["v2_cost10bp"] = fold_metrics(v2, "v2 @0.10%", cost=0.001)

# multi-asset B&H (DIA, QQQ, Mag-7 eq-weight) full-period CAGR/Sharpe/DD per fold
def bh_metrics_series(close, label):
    rows = []
    for name, a, b in FOLDS:
        c = close.loc[a:b].dropna()
        if len(c) < 100: rows.append({"label": f"{label} {name}", "note": "insufficient history"}); continue
        s = pd.Series(1.0, index=c.index)
        rows.append(ve.metrics(c, s, 0.0, None, f"{label} {name}"))
    return rows
uni = loader.load_universe(["DIA","QQQ","AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"])
uni = uni[uni.index < HOLDOUT_START]
mag7 = uni[["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"]].pct_change()
mag7_r = mag7.mean(axis=1, skipna=True).fillna(0.0)   # eq-weight, daily rebal, available names
mag7_px = 100*(1+mag7_r).cumprod()
out["baselines"]["DIA B&H"] = bh_metrics_series(uni["DIA"], "DIA")
out["baselines"]["QQQ B&H"] = bh_metrics_series(uni["QQQ"], "QQQ")
out["baselines"]["Mag7 eqw"] = bh_metrics_series(mag7_px, "Mag7")

# ---------------- E1: wider vol-target grid ----------------
e1_sharpes_all = []
for tv in [0.21, 0.24, 0.27, 0.30]:
    for lb in [20, 60, 120]:
        sig = vol_target.signals(spy, target_vol=tv, lookback=lb)
        ss = wf_sharpes(sig)
        e1_sharpes_all += ss
        out["E1"].append({"tv": tv, "lb": lb, "wf_sharpes": ss, "mean": round(np.mean(ss),3)})
v2_ss = wf_sharpes(v2); out["v2_wf"] = {"sharpes": v2_ss, "mean": round(np.mean(v2_ss),3)}
v1_ss = wf_sharpes(v1); out["v1_wf"] = {"sharpes": v1_ss, "mean": round(np.mean(v1_ss),3)}

# ---------------- E2: VIX percentile overlay on v2 ----------------
vix_pct = vix.rolling(756, min_periods=252).rank(pct=True)
e2_trials = []
for pct in [0.70, 0.80, 0.90]:
    for scale in [0.5, 0.0]:
        gate = pd.Series(np.where(vix_pct > pct, scale, 1.0), index=spy.index)
        sig = (v2 * gate).clip(0, 1)
        ss = wf_sharpes(sig)
        mm = fold_metrics(sig, f"v2xVIX p{int(pct*100)}/s{scale}")
        dd = min(m["MaxDD"] for m in mm)
        e2_trials.append({"pct": pct, "scale": scale, "wf_sharpes": ss,
                          "mean": round(np.mean(ss),3), "worstDD": dd})
out["E2"] = e2_trials

# ---------------- significance on best E2 vs incumbent v2 ----------------
best = max(e2_trials, key=lambda d: d["mean"])
gate = pd.Series(np.where(vix_pct > best["pct"], best["scale"], 1.0), index=spy.index)
sig_best = (v2 * gate).clip(0, 1)
oos_a, oos_b = "2020-01-01", "2025-07-11"
r_best, r_v2 = rets(sig_best, oos_a, oos_b), rets(v2, oos_a, oos_b)
r_spy = rets(one, oos_a, oos_b)
all_trial_sh = [s for t in e2_trials for s in t["wf_sharpes"]]
out["E2_sig"] = {
 "best": {k: best[k] for k in ("pct","scale","mean","worstDD")},
 "dsr_best": round(ev.deflated_sharpe_ratio(r_best, all_trial_sh), 4),
 "ci_vs_spy": ev.bootstrap_difference_ci(r_best, r_spy).__dict__,
 "ci_vs_v2": ev.bootstrap_difference_ci(r_best, r_v2).__dict__,
}
# v2 itself vs SPY on 2020-2025H real data (graduation criterion 1 check)
out["v2_vs_spy_oos"] = {
 "dsr_v2": round(ev.deflated_sharpe_ratio(r_v2, e1_sharpes_all + v2_ss), 4),
 "ci_vs_spy": ev.bootstrap_difference_ci(r_v2, r_spy).__dict__,
}

json.dump(out, open("research/results_2026_07_14.json","w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:5500])
