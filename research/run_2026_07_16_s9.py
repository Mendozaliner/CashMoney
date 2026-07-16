"""Session 9 (2026-07-16): E14, E15, E16 — three new investing philosophies.

E14: Harry Browne Permanent Portfolio (SPY/TLT/GLD/SHY, 25% each + drift rebal)
E15: Blended Multi-Lookback Time-Series Momentum (1+3+6+12 month composite)
E16: Adaptive Asset Allocation (top-N momentum + min-variance weighting)

Data is fresh through 2026-07-15 (SPY $754.81). New mark update embedded.
"""
import sys, json
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, blended_momentum as bm, permanent_portfolio as pp, adaptive_alloc as aaa
from research.preregister import preregister, record_outcome, trials_this_period

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
HOLDOUT_START = "2025-07-16"   # 12-month holdout locked (updated for today)
COST = 0.0015
FOLDS = [
    ("2000-2009", "2000-01-01", "2009-12-31"),
    ("2010-2019", "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-15"),   # latest available
]
OOS_A, OOS_B = "2020-01-01", "2025-07-15"

# Full universe panel (stop before holdout)
full_panel = loader.load_universe(
    ["SPY", "TLT", "GLD", "SHY", "IEF", "IWM", "EFA", "DBC", "QQQ", "DIA",
     "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
)
panel = full_panel[full_panel.index < HOLDOUT_START].copy()

spy = panel["SPY"].dropna()
irx = loader.load_ohlcv("^IRX")["Close"].reindex(panel.index).ffill()
rf_daily = (irx / 100.0) / 252.0

# Champion v2 for comparison
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST,
                           rf_daily=rf_daily.reindex(spy.index).fillna(0.0))
spy_ret = spy.pct_change().fillna(0.0)

print(f"Data through: {panel.index[-1].date()}")
print(f"SPY last close: {spy.iloc[-1]:.2f}")
print(f"Total registered configs so far: {trials_this_period()}")
print()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def wf_metrics(r, label=""):
    """Walk-forward fold Sharpes + mean + worst DD + OOS Sharpe."""
    fold_sharpes = []
    worst_dd = 0.0
    for name, a, b in FOLDS:
        x = r.loc[a:b]
        if len(x) < 60:
            fold_sharpes.append(0.0)
            continue
        sh = ev.sharpe_ratio(x)
        fold_sharpes.append(round(sh, 3))
        eq = (1 + x).cumprod()
        dd = float((eq / eq.cummax() - 1).min())
        worst_dd = min(worst_dd, dd)
    mean_wf = float(np.mean(fold_sharpes))
    oos = r.loc[OOS_A:OOS_B]
    oos_sh = ev.sharpe_ratio(oos)
    end1k = float((1 + r).prod() * 1000)
    return {
        "label": label,
        "folds": fold_sharpes,
        "mean_wf": round(mean_wf, 3),
        "worst_dd": round(worst_dd * 100, 2),
        "oos_sharpe": round(oos_sh, 3),
        "end1k": round(end1k, 2),
    }


def significance_check(r, trial_sharpes, label):
    oos = r.loc[OOS_A:OOS_B]
    spy_oos = spy_ret.reindex(oos.index).fillna(0.0)
    a1, a2 = oos.align(spy_oos, join="inner")
    dsr = ev.deflated_sharpe_ratio(a1, trial_sharpes)
    ci = ev.bootstrap_difference_ci(a1, a2)
    print(f"  {label}: DSR={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}]  clears={ci.clears_noise}")
    return dsr, ci


# ============================================================================
# E14: Harry Browne Permanent Portfolio
# ============================================================================
print("=" * 60)
print("E14: Harry Browne Permanent Portfolio")
print("=" * 60)

reg14 = preregister(
    hypothesis=(
        "The Harry Browne Permanent Portfolio (25% each SPY/TLT/GLD/SHY with "
        "month-end rebalancing when any slot drifts ≥5%) produces a regime-agnostic "
        "return stream that is genuinely uncorrelated with v2's equity-trend signal, "
        "and delivers superior risk-adjusted returns (Sharpe ≥ v2's 0.844) in walk-"
        "forward testing. The four assets are mechanically counter-cyclical (SPY: "
        "prosperity; TLT: deflation; GLD: inflation; SHY: recession/fear), so the "
        "blend should be smoother than any single-regime strategy."
    ),
    success_criteria=(
        "Deflated Sharpe ≥ 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0 "
        "AND worst-fold MaxDD shallower than -20% AND mean WF Sharpe ≥ 0.844. "
        "If adopted, also compare raw terminal value vs v2 and SPY."
    ),
    grid_size=4,
    primary_metric="sharpe"
)
print(f"Registered: {reg14.id}")

pp_panel = panel[["SPY", "TLT", "GLD", "SHY"]].copy()
rows14, trial_sharpes14 = [], []
for band in (0.0, 0.05, 0.10, 0.15):
    w = pp.multi_signals(pp_panel, band=band)
    r = me.portfolio_returns(pp_panel, w, commission=COST, rf_daily=rf_daily)
    m = wf_metrics(r, f"PP(band={band})")
    trial_sharpes14.append(ev.sharpe_ratio(r.loc[OOS_A:OOS_B]))
    rows14.append(m)
    print(m)

best14 = max(rows14, key=lambda x: x["mean_wf"])
print(f"\nBest config: {best14['label']}")
# Find returns for best config
band_best14 = float(best14["label"].split("=")[1].rstrip(")"))
w_best14 = pp.multi_signals(pp_panel, band=band_best14)
r_best14 = me.portfolio_returns(pp_panel, w_best14, commission=COST, rf_daily=rf_daily)
dsr14, ci14 = significance_check(r_best14, trial_sharpes14, best14["label"])

ok14 = (dsr14 >= 0.95 and ci14.lo > 0 and best14["worst_dd"] > -20 and best14["mean_wf"] >= 0.844)
verdict14 = "adopted" if ok14 else "discarded"
print(f"VERDICT: {verdict14.upper()}")

# Correlation with v2
oos14 = r_best14.loc[OOS_A:OOS_B]
oos_v2 = r_v2.reindex(oos14.index).fillna(0.0)
corr14 = float(pd.concat([oos14, oos_v2], axis=1).dropna().corr().iloc[0, 1])
print(f"Correlation with v2 (OOS): {corr14:.3f}")

record_outcome(reg14.id, verdict=verdict14,
               evidence={"best": best14, "all_rows": rows14,
                         "dsr": round(dsr14, 4),
                         "diff_ci": [round(ci14.lo, 3), round(ci14.hi, 3)],
                         "corr_v2": round(corr14, 3)})
print()


# ============================================================================
# E15: Blended Multi-Lookback Momentum
# ============================================================================
print("=" * 60)
print("E15: Blended Multi-Lookback Time-Series Momentum")
print("=" * 60)

reg15 = preregister(
    hypothesis=(
        "Averaging time-series momentum signals across four lookbacks (1, 3, 6, 12 "
        "months) produces a smoother, less whipsaw-prone exposure than the champion "
        "v2's pure SMA200 trend gate. When all four lookbacks agree (composite=1.0), "
        "position is fully scaled by vol target; when lookbacks disagree, exposure is "
        "fractional. Combined with the same SMA200 trend gate and 18% vol target as v2, "
        "the hypothesis is: composite >= v2 Sharpe with lower worst-fold DD."
    ),
    success_criteria=(
        "Deflated Sharpe ≥ 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0 "
        "AND worst-fold MaxDD shallower than -20% AND mean WF Sharpe ≥ v2's 0.844."
    ),
    grid_size=6,
    primary_metric="sharpe"
)
print(f"Registered: {reg15.id}")

rows15, trial_sharpes15 = [], []
for n_lb in (2, 3, 4):
    for tv in (0.15, 0.18):
        sig = bm.signals(spy, target_vol=tv, n_lookbacks=n_lb)
        r = ve.strategy_returns(spy, sig, commission=COST,
                               rf_daily=rf_daily.reindex(spy.index).fillna(0.0))
        m = wf_metrics(r, f"BM(n_lb={n_lb},tv={tv})")
        trial_sharpes15.append(ev.sharpe_ratio(r.loc[OOS_A:OOS_B]))
        rows15.append({**m, "_r": r})
        print({k: v for k, v in m.items() if k != "_r"})

best15 = max(rows15, key=lambda x: x["mean_wf"])
print(f"\nBest config: {best15['label']}")
r_best15 = best15["_r"]
dsr15, ci15 = significance_check(r_best15, trial_sharpes15, best15["label"])

ok15 = (dsr15 >= 0.95 and ci15.lo > 0 and best15["worst_dd"] > -20 and best15["mean_wf"] >= 0.844)
verdict15 = "adopted" if ok15 else "discarded"
print(f"VERDICT: {verdict15.upper()}")

corr15 = float(pd.concat([r_best15.loc[OOS_A:OOS_B], oos_v2], axis=1).dropna().corr().iloc[0, 1])
print(f"Correlation with v2 (OOS): {corr15:.3f}")

record_outcome(reg15.id, verdict=verdict15,
               evidence={"best": {k: v for k, v in best15.items() if k != "_r"},
                         "all_rows": [{k: v for k, v in r.items() if k != "_r"} for r in rows15],
                         "dsr": round(dsr15, 4),
                         "diff_ci": [round(ci15.lo, 3), round(ci15.hi, 3)],
                         "corr_v2": round(corr15, 3)})
print()


# ============================================================================
# E16: Adaptive Asset Allocation
# ============================================================================
print("=" * 60)
print("E16: Adaptive Asset Allocation (top-N + min-var)")
print("=" * 60)

reg16 = preregister(
    hypothesis=(
        "Adaptive Asset Allocation (Butler et al. 2012) adds correlation structure "
        "to momentum selection: select the top-N assets by trailing return, then weight "
        "them by minimum variance using a 60-day rolling covariance matrix. This should "
        "outperform equal-weight GTAA (E6, Sharpe 0.892 — failed DSR/CI) because the "
        "correlation-aware weights reduce portfolio variance without sacrificing the "
        "momentum selection effect. Universe: SPY/IWM/EFA/IEF/GLD/DBC."
    ),
    success_criteria=(
        "Deflated Sharpe ≥ 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0 "
        "AND worst-fold MaxDD shallower than -20% AND mean WF Sharpe ≥ 0.844."
    ),
    grid_size=6,
    primary_metric="sharpe"
)
print(f"Registered: {reg16.id}")

aaa_panel = panel[["SPY", "IWM", "EFA", "IEF", "GLD", "DBC"]].copy()
rows16, trial_sharpes16 = [], []
for top_n in (2, 3):
    for lookback in (3, 6, 12):
        w = aaa.multi_signals(aaa_panel, top_n=top_n, lookback=lookback)
        r = me.portfolio_returns(aaa_panel, w, commission=COST, rf_daily=rf_daily)
        m = wf_metrics(r, f"AAA(top{top_n},lb{lookback}mo)")
        trial_sharpes16.append(ev.sharpe_ratio(r.loc[OOS_A:OOS_B]))
        rows16.append({**m, "_r": r})
        print({k: v for k, v in m.items() if k != "_r"})

best16 = max(rows16, key=lambda x: x["mean_wf"])
print(f"\nBest config: {best16['label']}")
r_best16 = best16["_r"]
dsr16, ci16 = significance_check(r_best16, trial_sharpes16, best16["label"])

ok16 = (dsr16 >= 0.95 and ci16.lo > 0 and best16["worst_dd"] > -20 and best16["mean_wf"] >= 0.844)
verdict16 = "adopted" if ok16 else "discarded"
print(f"VERDICT: {verdict16.upper()}")

corr16 = float(pd.concat([r_best16.loc[OOS_A:OOS_B], oos_v2], axis=1).dropna().corr().iloc[0, 1])
print(f"Correlation with v2 (OOS): {corr16:.3f}")

record_outcome(reg16.id, verdict=verdict16,
               evidence={"best": {k: v for k, v in best16.items() if k != "_r"},
                         "all_rows": [{k: v for k, v in r.items() if k != "_r"} for r in rows16],
                         "dsr": round(dsr16, 4),
                         "diff_ci": [round(ci16.lo, 3), round(ci16.hi, 3)],
                         "corr_v2": round(corr16, 3)})
print()


# ============================================================================
# $1,000 Simulation — all strategies vs benchmarks (2026-07-15 fresh data)
# ============================================================================
print("=" * 60)
print("$1,000 SIMULATION (2000-01-01 to 2026-07-15, incl. holdout)")
print("=" * 60)

# Champion v2 (using full panel, no holdout exclusion for simulation)
full_spy = full_panel["SPY"].dropna()
full_irx = loader.load_ohlcv("^IRX")["Close"].reindex(full_panel.index).ffill()
full_rf = (full_irx / 100.0) / 252.0

sig_v2_full = vol_target.signals(full_spy, target_vol=0.18, lookback=20)
r_v2_full = ve.strategy_returns(full_spy, sig_v2_full, commission=COST,
                                rf_daily=full_rf.reindex(full_spy.index).fillna(0.0))

# Benchmarks
results_1k = {}
for t in ["SPY", "QQQ", "DIA", "IWM"]:
    s = full_panel[t].dropna()
    r = s.pct_change().fillna(0.0)
    results_1k[t] = {"end1k": round(float((1 + r).prod() * 1000), 2),
                     "sharpe": round(ev.sharpe_ratio(r), 3)}

# Mag-7 equal-weight (from 2012 when all 7 are available)
mag7_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
mag7_panel = full_panel[mag7_tickers].dropna()
mag7_r = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
results_1k["Mag7-EW"] = {"end1k": round(float((1 + mag7_r).prod() * 1000), 2),
                          "sharpe": round(ev.sharpe_ratio(mag7_r), 3),
                          "note": f"from {mag7_panel.index[0].date()}"}

results_1k["v2-champion"] = {"end1k": round(float((1 + r_v2_full).prod() * 1000), 2),
                              "sharpe": round(ev.sharpe_ratio(r_v2_full), 3)}

# New strategies (full data including holdout)
# E14 best
w_pp_full = pp.multi_signals(full_panel[["SPY", "TLT", "GLD", "SHY"]], band=band_best14)
r_pp_full = me.portfolio_returns(full_panel[["SPY", "TLT", "GLD", "SHY"]],
                                  w_pp_full, commission=COST, rf_daily=full_rf)
results_1k["E14-PermPort"] = {"end1k": round(float((1 + r_pp_full).prod() * 1000), 2),
                               "sharpe": round(ev.sharpe_ratio(r_pp_full), 3)}

# E15 best
bm_params = best15["label"]   # e.g. "BM(n_lb=4,tv=0.18)"
import re
m = re.search(r"n_lb=(\d+),tv=([\d.]+)", bm_params)
best_nlb = int(m.group(1)); best_tv = float(m.group(2))
sig_bm_full = bm.signals(full_spy, target_vol=best_tv, n_lookbacks=best_nlb)
r_bm_full = ve.strategy_returns(full_spy, sig_bm_full, commission=COST,
                                 rf_daily=full_rf.reindex(full_spy.index).fillna(0.0))
results_1k["E15-BlendMom"] = {"end1k": round(float((1 + r_bm_full).prod() * 1000), 2),
                               "sharpe": round(ev.sharpe_ratio(r_bm_full), 3)}

# E16 best
aaa_params = best16["label"]  # e.g. "AAA(top3,lb6mo)"
m2 = re.search(r"top(\d+),lb(\d+)mo", aaa_params)
best_topn = int(m2.group(1)); best_lb = int(m2.group(2))
aaa_full_panel = full_panel[["SPY", "IWM", "EFA", "IEF", "GLD", "DBC"]].copy()
w_aaa_full = aaa.multi_signals(aaa_full_panel, top_n=best_topn, lookback=best_lb)
r_aaa_full = me.portfolio_returns(aaa_full_panel, w_aaa_full, commission=COST, rf_daily=full_rf)
results_1k["E16-AAA"] = {"end1k": round(float((1 + r_aaa_full).prod() * 1000), 2),
                          "sharpe": round(ev.sharpe_ratio(r_aaa_full), 3)}

print("\n$1k simulation results (2000-01-01 to 2026-07-15):")
for name, m in sorted(results_1k.items(), key=lambda x: -x[1]["end1k"]):
    note = m.get("note", "")
    print(f"  {name:20s}: ${m['end1k']:>10,.2f}  Sharpe {m['sharpe']:.3f}  {note}")

# ============================================================================
# Final summary
# ============================================================================
print()
print(f"Total registered configs (cumulative): {trials_this_period()}")

# Save results
results = {
    "E14_permanent_portfolio": {"rows": rows14, "best": best14,
                                "dsr": round(dsr14, 4),
                                "diff_ci": [round(ci14.lo, 3), round(ci14.hi, 3)],
                                "corr_v2": round(corr14, 3), "verdict": verdict14},
    "E15_blended_momentum": {"rows": [{k: v for k, v in r.items() if k != "_r"} for r in rows15],
                              "best": {k: v for k, v in best15.items() if k != "_r"},
                              "dsr": round(dsr15, 4),
                              "diff_ci": [round(ci15.lo, 3), round(ci15.hi, 3)],
                              "corr_v2": round(corr15, 3), "verdict": verdict15},
    "E16_adaptive_alloc": {"rows": [{k: v for k, v in r.items() if k != "_r"} for r in rows16],
                            "best": {k: v for k, v in best16.items() if k != "_r"},
                            "dsr": round(dsr16, 4),
                            "diff_ci": [round(ci16.lo, 3), round(ci16.hi, 3)],
                            "corr_v2": round(corr16, 3), "verdict": verdict16},
    "sim_1k": results_1k,
}
json.dump(results, open("research/results_2026_07_16_s9.json", "w"), indent=1)
print("Results saved to research/results_2026_07_16_s9.json")
