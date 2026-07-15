"""Session 7 (2026-07-15) experiment runner.

Addresses three roadmap items and a correlation feasibility memo:
  E9:  True Antonacci GEM — SPY/EFA/EEM equity rotation vs SHY bar, AGG harbor.
       (Roadmap item 0: true international GEM, now that EFA/EEM/AGG are cached.)
  E10: True Faber GTAA-5 — SPY/EFA/IEF/VNQ/DBC, 5-asset-class trend gating.
       (Roadmap item 0: true GTAA-5, now that VNQ/DBC are cached.)
  E11: Sector Momentum + Trend Gate — retry E5 with per-sector SMA200 filter.
       (Roadmap item 4: trend gate prevents XLK momentum crash entry 2000-01.)
  M1:  GTAA Correlation Memo — v2 vs GTAA(w150,b0) daily return correlation.
       (Roadmap item 2: ensemble feasibility check before registering a test.)

All experiments pre-registered BEFORE results. 18 configs total this session.
Walk-forward folds: 2000-2009 / 2010-2019 / 2020-2025H (locked final 12 months).
Data constraints noted per experiment: EFA/EEM/AGG/VNQ/DBC have 2001-2006 starts.
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, gtaa, sector_trend, gem
from research.preregister import preregister, record_outcome, trials_this_period

HOLDOUT_START = "2025-07-14"
COST = 0.0015
FOLDS = [
    ("2000-2009",  "2000-01-01", "2009-12-31"),
    ("2010-2019",  "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-11"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-11"

# ── Data loading ──────────────────────────────────────────────────────────────
freshness = loader.data_freshness()
print(f"Data freshness: {freshness}")

spy_full = loader.load_ohlcv("SPY")["Close"]
spy = spy_full[spy_full.index < HOLDOUT_START]
irx = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily = (irx / 100.0) / 252.0

# Core universe (v2 baseline + GTAA assets)
UNIVERSE_CORE = ["SPY", "QQQ", "DIA", "IWM", "IEF", "SHY", "GLD", "TLT"]
# E9 GEM universe: needs EFA, EEM, AGG
UNIVERSE_GEM  = ["SPY", "EFA", "EEM", "SHY", "AGG"]
# E10 GTAA-5 universe: needs VNQ, DBC
UNIVERSE_G5   = ["SPY", "EFA", "IEF", "VNQ", "DBC"]
# E11 sector universe
UNIVERSE_SEC  = ["XLK", "XLF", "XLE", "XLV", "XLY",
                 "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC"]
# Mag-7 for benchmark
UNIVERSE_MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

panel_core = loader.load_universe(UNIVERSE_CORE)[
    lambda df: df.index < HOLDOUT_START
]
panel_gem  = loader.load_universe(UNIVERSE_GEM)[
    lambda df: df.index < HOLDOUT_START
]
panel_g5   = loader.load_universe(UNIVERSE_G5)[
    lambda df: df.index < HOLDOUT_START
]
panel_sec  = loader.load_universe(UNIVERSE_SEC)[
    lambda df: df.index < HOLDOUT_START
]
panel_mag7 = loader.load_universe(UNIVERSE_MAG7)

print(f"Panels loaded: core={panel_core.shape} gem={panel_gem.shape} "
      f"g5={panel_g5.shape} sec={panel_sec.shape}")
print(f"GEM universe columns: {list(panel_gem.columns)}")
print(f"GTAA-5 universe columns: {list(panel_g5.columns)}")

# ── Pre-registration ──────────────────────────────────────────────────────────
prior = trials_this_period()
print(f"Prior total configs registered: {prior}")

reg_e9 = preregister(
    hypothesis=(
        "True Antonacci GEM with international equity rotation (SPY vs EFA/EEM vs SHY, "
        "AGG defensive harbor) provides genuine cross-country diversification that the "
        "failed E3/E7 (domestic-only SPY/QQQ/DIA) lacked. International rotation adds "
        "a second dimension of momentum beyond just the SHY absolute bar, and AGG avoids "
        "the 2022 TLT duration catastrophe that killed E3 (-42.6% DD). Key hypothesis: "
        "country rotation (not just SHY vs equity) is what makes GEM work long-term."
    ),
    success_criteria=(
        "OOS (2020-2025H) deflated-Sharpe >= 0.95 for 6 trials AND diff-vs-SPY "
        "bootstrap CI lower bound > 0 AND worst-fold MaxDD < -30% (relaxed from -20% "
        "given country rotation nature) AND mean WF Sharpe >= v2's 0.844. "
        "Note: fold-1 results are truncated by EEM/AGG availability (2003+); "
        "do not penalize fold-1 performance vs full-history strategies."
    ),
    grid_size=6, primary_metric="sharpe"
)

reg_e10 = preregister(
    hypothesis=(
        "True Faber GTAA-5 (SPY/EFA/IEF/VNQ/DBC) with 5 asset classes provides genuine "
        "cross-asset-class diversification that the prior 4-asset GTAA (E6, SPY/IWM/IEF/GLD) "
        "lacked. Adding VNQ (real estate) and DBC (commodities) introduces inflation hedges "
        "and uncorrelated return streams. The 2022 crisis, where bonds AND stocks fell, "
        "may be mitigated by commodity exposure via DBC."
    ),
    success_criteria=(
        "OOS (2020-2025H) deflated-Sharpe >= 0.95 for 6 trials AND diff-vs-SPY "
        "bootstrap CI lower bound > 0 AND worst-fold MaxDD better (shallower) than -20% "
        "AND mean WF Sharpe >= v2's 0.844. Note: DBC starts 2006; fold-1 is severely "
        "truncated (only 2006-2009 data). Flag fold-1 as partial and weight fold-2/3 "
        "more heavily in the assessment."
    ),
    grid_size=6, primary_metric="sharpe"
)

reg_e11 = preregister(
    hypothesis=(
        "Sector momentum with per-sector SMA200 trend gate (retry of E5) fixes the "
        "dot-com failure mode: XLK above its SMA200 in late 1999/early 2000 would have "
        "blocked it from entering the bubble top. The gate forces BOTH trend (SMA200) "
        "AND momentum agreement before taking a sector position. E5 failed with -51.8% "
        "DD; the gate is expected to cut worst-fold DD substantially while preserving "
        "the cross-sectional momentum edge in confirmed uptrend sectors."
    ),
    success_criteria=(
        "Worst-fold MaxDD materially better than E5's -51.8% (target: < -35%) AND "
        "mean WF Sharpe >= v2's 0.844 AND OOS deflated-Sharpe >= 0.95 for 6 trials "
        "AND diff-vs-SPY CI lower bound > 0. "
        "Accept: if the gate cuts DD to < -35% even if SPY significance is not met, "
        "note it as a partial result and keep for ensemble research."
    ),
    grid_size=6, primary_metric="sharpe"
)

print(f"Registered: E9={reg_e9.id} E10={reg_e10.id} E11={reg_e11.id}")

# ── Helper functions ──────────────────────────────────────────────────────────
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
        out.append(round(float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0, 3))
    return out

def multi_fold_metrics(weights, pan, label, cost=COST):
    return [me.metrics(pan.loc[a:b], weights.loc[a:b], cost, rf_daily.loc[a:b],
                       f"{label} {n}") for n, a, b in FOLDS]

def multi_oos_returns(weights, pan, cost=COST):
    sr = me.portfolio_returns(pan.loc[OOS_A:OOS_B], weights.loc[OOS_A:OOS_B],
                              cost, rf_daily.loc[OOS_A:OOS_B])
    return sr[sr.index > sr.index[0]]

r_spy_oos = spy.loc[OOS_A:OOS_B].pct_change().fillna(0.0)[1:]

# ── Baseline v2 ───────────────────────────────────────────────────────────────
v2_sig = vol_target.signals(spy, target_vol=0.18, lookback=20)
v2_wf = single_fold_sharpes(v2_sig)
v2_folds = single_fold_metrics(v2_sig, "v2")
print(f"\n[BASELINE] v2 WF Sharpes: {v2_wf} mean={np.mean(v2_wf):.3f}")

results = {
    "session": "2026-07-15-s7",
    "data_freshness": freshness,
    "v2_baseline_wf_sharpes": v2_wf,
    "E9": [], "E10": [], "E11": [],
}

# ── $1,000 benchmark test (full history 2000-2026-07-14) ─────────────────────
print("\n" + "=" * 60 + "\n$1,000 BENCHMARK TEST (2000-01-01 → 2026-07-14)")
spy_full_bench = loader.load_ohlcv("SPY")["Close"]
irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_full_bench.index).ffill()
rf_full = (irx_full / 100.0) / 252.0

def bench_dollar(close, label, cost=0.0):
    r = close.pct_change().fillna(0.0)
    eq = (1 + r).cumprod() * 1000
    return round(float(eq.iloc[-1]), 2)

def bench_sharpe(close):
    r = close.pct_change().fillna(0.0)[1:]
    return round(float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0, 3)

def strategy_dollar(sig, close, rf, cost=COST):
    r = ve.strategy_returns(close, sig, cost, rf)
    eq = (1 + r).cumprod() * 1000
    return round(float(eq.iloc[-1]), 2)

v2_sig_full = vol_target.signals(spy_full_bench, target_vol=0.18, lookback=20)
v2_dollar = strategy_dollar(v2_sig_full, spy_full_bench, rf_full)

benchmarks = {
    "SPY B&H":  bench_dollar(spy_full_bench, "SPY"),
    "DIA B&H":  bench_dollar(loader.load_ohlcv("DIA")["Close"], "DIA"),
    "QQQ B&H":  bench_dollar(loader.load_ohlcv("QQQ")["Close"], "QQQ"),
    "v2 (champ)": v2_dollar,
}

# Mag-7 equal-weight (start when all 7 are available: GOOGL starts 2004-08,
# META starts 2012-05, TSLA starts 2010-06 — use 2012-06 start)
mag7_start = "2012-06-01"
mag7_pan = panel_mag7[panel_mag7.index >= mag7_start]
mag7_weights = pd.DataFrame(1.0 / 7.0, index=mag7_pan.index, columns=panel_mag7.columns)
mag7_rf = rf_full.reindex(mag7_pan.index).ffill()
mag7_r = me.portfolio_returns(mag7_pan, mag7_weights, commission=0.0, rf_daily=None)
mag7_eq = (1 + mag7_r).cumprod() * 1000
benchmarks["Mag-7 eqw (2012+)"] = round(float(mag7_eq.iloc[-1]), 2)

spy_since_mag7 = spy_full_bench[spy_full_bench.index >= mag7_start]
benchmarks["SPY B&H (2012+)"] = bench_dollar(spy_since_mag7, "SPY 2012+")

print("  $1,000 test results:")
for name, val in benchmarks.items():
    print(f"    {name}: ${val:,.2f}")
results["benchmark_test"] = benchmarks

# ── E9: True Antonacci GEM ────────────────────────────────────────────────────
print("\n" + "=" * 60 + "\nE9: True Antonacci GEM (SPY/EFA/EEM vs SHY, AGG harbor)")
e9_configs = [{"lookback": lb, "skip": sk} for lb in [126, 210, 252] for sk in [0, 21]]
e9_all_sharpes = []

for cfg in e9_configs:
    w = gem.multi_signals(panel_gem, **cfg)
    sh = multi_fold_sharpes(w, panel_gem)
    e9_all_sharpes.extend(sh)
    mm = multi_fold_metrics(w, panel_gem, f"GEM lb{cfg['lookback']} sk{cfg['skip']}")
    worst_dd = min(f["MaxDD"] for f in mm)
    results["E9"].append({
        "cfg": cfg, "wf_sharpes": sh,
        "mean": round(float(np.mean(sh)), 3), "folds": mm
    })
    print(f"  lb={cfg['lookback']} sk={cfg['skip']}: WF={sh} "
          f"mean={np.mean(sh):.3f} worstDD={worst_dd:.1f}%")

best_e9 = max(results["E9"], key=lambda d: d["mean"])
w_e9 = gem.multi_signals(panel_gem, **best_e9["cfg"])
r_e9 = multi_oos_returns(w_e9, panel_gem)
dsr_e9 = ev.deflated_sharpe_ratio(r_e9.values, e9_all_sharpes)
ci_e9 = ev.bootstrap_difference_ci(r_e9.values, r_spy_oos.reindex(r_e9.index).values)
worst_dd_e9 = min(f["MaxDD"] for f in best_e9["folds"])
results["E9_sig"] = {
    "best_cfg": best_e9["cfg"], "mean_wf": best_e9["mean"],
    "dsr": round(float(dsr_e9), 4),
    "ci": [round(float(ci_e9.lo), 3), round(float(ci_e9.hi), 3)],
    "clears": bool(ci_e9.clears_noise), "worst_dd": worst_dd_e9
}
e9_verdict = ("PASS" if (dsr_e9 >= 0.95 and ci_e9.clears_noise and
                          worst_dd_e9 > -30.0 and best_e9["mean"] >= 0.844)
              else "FAIL")
print(f"  BEST {best_e9['cfg']} mean={best_e9['mean']:.3f} DSR={dsr_e9:.4f} "
      f"CI=[{ci_e9.lo:.3f},{ci_e9.hi:.3f}] worstDD={worst_dd_e9:.1f}% → {e9_verdict}")
results["E9_verdict"] = e9_verdict

verdict_e9 = "adopted" if e9_verdict == "PASS" else "discarded"
record_outcome(reg_e9.id, verdict=verdict_e9, notes=str(results["E9_sig"]))

# ── E10: True Faber GTAA-5 ───────────────────────────────────────────────────
print("\n" + "=" * 60 + "\nE10: True Faber GTAA-5 (SPY/EFA/IEF/VNQ/DBC)")
GTAA5_ASSETS = ["SPY", "EFA", "IEF", "VNQ", "DBC"]
e10_configs = [{"window": w, "band": b, "assets": GTAA5_ASSETS}
               for w in [150, 200, 250] for b in [0.0, 0.02]]
e10_all_sharpes = []

for cfg in e10_configs:
    w = gtaa.multi_signals(panel_g5, **cfg)
    sh = multi_fold_sharpes(w, panel_g5)
    e10_all_sharpes.extend(sh)
    cfg_display = {"window": cfg["window"], "band": cfg["band"]}
    mm = multi_fold_metrics(w, panel_g5, f"GTAA5 w{cfg['window']} b{cfg['band']}")
    worst_dd = min(f["MaxDD"] for f in mm)
    results["E10"].append({
        "cfg": cfg_display, "wf_sharpes": sh,
        "mean": round(float(np.mean(sh)), 3), "folds": mm
    })
    print(f"  w={cfg['window']} b={cfg['band']}: WF={sh} "
          f"mean={np.mean(sh):.3f} worstDD={worst_dd:.1f}%")

best_e10 = max(results["E10"], key=lambda d: d["mean"])
best_e10_cfg = {"window": best_e10["cfg"]["window"],
                "band": best_e10["cfg"]["band"],
                "assets": GTAA5_ASSETS}
w_e10 = gtaa.multi_signals(panel_g5, **best_e10_cfg)
r_e10 = multi_oos_returns(w_e10, panel_g5)
dsr_e10 = ev.deflated_sharpe_ratio(r_e10.values, e10_all_sharpes)
ci_e10 = ev.bootstrap_difference_ci(r_e10.values, r_spy_oos.reindex(r_e10.index).values)
worst_dd_e10 = min(f["MaxDD"] for f in best_e10["folds"])
results["E10_sig"] = {
    "best_cfg": best_e10["cfg"], "mean_wf": best_e10["mean"],
    "dsr": round(float(dsr_e10), 4),
    "ci": [round(float(ci_e10.lo), 3), round(float(ci_e10.hi), 3)],
    "clears": bool(ci_e10.clears_noise), "worst_dd": worst_dd_e10
}
e10_verdict = ("PASS" if (dsr_e10 >= 0.95 and ci_e10.clears_noise and
                           worst_dd_e10 > -20.0 and best_e10["mean"] >= 0.844)
               else "FAIL")
print(f"  BEST {best_e10['cfg']} mean={best_e10['mean']:.3f} DSR={dsr_e10:.4f} "
      f"CI=[{ci_e10.lo:.3f},{ci_e10.hi:.3f}] worstDD={worst_dd_e10:.1f}% → {e10_verdict}")
results["E10_verdict"] = e10_verdict

verdict_e10 = "adopted" if e10_verdict == "PASS" else "discarded"
record_outcome(reg_e10.id, verdict=verdict_e10, notes=str(results["E10_sig"]))

# ── E11: Sector Momentum + Trend Gate ────────────────────────────────────────
print("\n" + "=" * 60 + "\nE11: Sector Momentum + Trend Gate")
e11_configs = [{"lookback": lb, "top_n": n}
               for lb in [126, 252] for n in [1, 2, 3]]
e11_all_sharpes = []

for cfg in e11_configs:
    w = sector_trend.multi_signals(panel_sec, **cfg)
    sh = multi_fold_sharpes(w, panel_sec)
    e11_all_sharpes.extend(sh)
    mm = multi_fold_metrics(w, panel_sec, f"SecTrend lb{cfg['lookback']} n{cfg['top_n']}")
    worst_dd = min(f["MaxDD"] for f in mm)
    results["E11"].append({
        "cfg": cfg, "wf_sharpes": sh,
        "mean": round(float(np.mean(sh)), 3), "folds": mm
    })
    print(f"  lb={cfg['lookback']} n={cfg['top_n']}: WF={sh} "
          f"mean={np.mean(sh):.3f} worstDD={worst_dd:.1f}%")

best_e11 = max(results["E11"], key=lambda d: d["mean"])
w_e11 = sector_trend.multi_signals(panel_sec, **best_e11["cfg"])
r_e11 = multi_oos_returns(w_e11, panel_sec)
dsr_e11 = ev.deflated_sharpe_ratio(r_e11.values, e11_all_sharpes)
ci_e11 = ev.bootstrap_difference_ci(r_e11.values, r_spy_oos.reindex(r_e11.index).values)
worst_dd_e11 = min(f["MaxDD"] for f in best_e11["folds"])
results["E11_sig"] = {
    "best_cfg": best_e11["cfg"], "mean_wf": best_e11["mean"],
    "dsr": round(float(dsr_e11), 4),
    "ci": [round(float(ci_e11.lo), 3), round(float(ci_e11.hi), 3)],
    "clears": bool(ci_e11.clears_noise), "worst_dd": worst_dd_e11
}
e11_verdict = ("PASS" if (dsr_e11 >= 0.95 and ci_e11.clears_noise and
                           worst_dd_e11 > -35.0 and best_e11["mean"] >= 0.844)
               else "FAIL" if worst_dd_e11 <= -35.0
               else "PARTIAL" if worst_dd_e11 > -35.0 else "FAIL")
print(f"  BEST {best_e11['cfg']} mean={best_e11['mean']:.3f} DSR={dsr_e11:.4f} "
      f"CI=[{ci_e11.lo:.3f},{ci_e11.hi:.3f}] worstDD={worst_dd_e11:.1f}% → {e11_verdict}")
results["E11_verdict"] = e11_verdict

verdict_e11 = ("adopted" if e11_verdict == "PASS"
               else "inconclusive" if e11_verdict == "PARTIAL"
               else "discarded")
record_outcome(reg_e11.id, verdict=verdict_e11, notes=str(results["E11_sig"]))

# ── M1: GTAA Correlation Memo ─────────────────────────────────────────────────
print("\n" + "=" * 60 + "\nM1: GTAA Correlation Memo (v2 vs GTAA w150/b0)")
GTAA_ASSETS = ["SPY", "IWM", "IEF", "GLD"]
gtaa_pan_full = loader.load_universe(GTAA_ASSETS + ["^IRX"])

w_gtaa = gtaa.multi_signals(
    gtaa_pan_full[GTAA_ASSETS][lambda df: df.index < HOLDOUT_START],
    window=150, band=0.0, assets=GTAA_ASSETS
)
gtaa_pan_corr = gtaa_pan_full[GTAA_ASSETS][lambda df: df.index < HOLDOUT_START]
rf_corr = (gtaa_pan_full["^IRX"][lambda df: df.index < HOLDOUT_START] / 100.0) / 252.0

r_gtaa_daily = me.portfolio_returns(gtaa_pan_corr, w_gtaa, COST, rf_corr)
r_v2_daily = ve.strategy_returns(spy, v2_sig, COST, rf_daily)

# Align on common dates
common = r_gtaa_daily.index.intersection(r_v2_daily.index)
rg = r_gtaa_daily.reindex(common).fillna(0.0)
rv = r_v2_daily.reindex(common).fillna(0.0)

corr_full = float(pd.Series(rg.values).corr(pd.Series(rv.values)))

fold_corrs = []
for name, a, b in FOLDS:
    rg_f = rg.loc[a:b]
    rv_f = rv.loc[a:b]
    c = float(pd.Series(rg_f.values).corr(pd.Series(rv_f.values)))
    fold_corrs.append({"fold": name, "corr": round(c, 3)})
    print(f"  Fold {name}: corr(GTAA, v2) = {c:.3f}")

print(f"  Full-period correlation: {corr_full:.3f}")
ensemble_feasible = abs(corr_full) < 0.70

# Equal-weight ensemble backtest (50% v2 + 50% GTAA)
rg_oos = r_gtaa_daily.loc[OOS_A:OOS_B]
rv_oos = r_v2_daily.loc[OOS_A:OOS_B]
common_oos = rg_oos.index.intersection(rv_oos.index)
ensemble_r = 0.5 * rg_oos.reindex(common_oos) + 0.5 * rv_oos.reindex(common_oos)
ensemble_sharpe = float(ensemble_r.mean() / ensemble_r.std() * np.sqrt(252))
v2_oos_sharpe = float(rv_oos.reindex(common_oos).mean() / rv_oos.reindex(common_oos).std() * np.sqrt(252))
gtaa_oos_sharpe = float(rg_oos.reindex(common_oos).mean() / rg_oos.reindex(common_oos).std() * np.sqrt(252))

# $1,000 projection of ensemble since 2000
r_v2_full_all = ve.strategy_returns(spy_full_bench, v2_sig_full, COST, rf_full)
r_gtaa_full = me.portfolio_returns(
    loader.load_universe(GTAA_ASSETS)[lambda df: df.index < HOLDOUT_START],
    gtaa.multi_signals(
        loader.load_universe(GTAA_ASSETS)[lambda df: df.index < HOLDOUT_START],
        window=150, band=0.0, assets=GTAA_ASSETS
    ), COST, rf_full.reindex(
        loader.load_universe(GTAA_ASSETS)[lambda df: df.index < HOLDOUT_START].index
    ).ffill()
)
common_all = r_v2_full_all.index.intersection(r_gtaa_full.index)
ens_full = 0.5 * r_v2_full_all.reindex(common_all) + 0.5 * r_gtaa_full.reindex(common_all)
ens_dollar = round(float((1 + ens_full).cumprod().iloc[-1] * 1000), 2)
ens_eq = (1 + ens_full).cumprod()
ens_dd = round(float((ens_eq / ens_eq.cummax() - 1).min() * 100), 2)

print(f"  OOS Sharpe — v2: {v2_oos_sharpe:.3f} | GTAA: {gtaa_oos_sharpe:.3f} | "
      f"50/50 ensemble: {ensemble_sharpe:.3f}")
print(f"  Ensemble $1k (2000→): ${ens_dollar:,.2f} | MaxDD: {ens_dd:.1f}%")
print(f"  Ensemble feasible (corr < 0.70): {ensemble_feasible}")

results["M1_correlation_memo"] = {
    "full_period_corr": round(corr_full, 3),
    "fold_corrs": fold_corrs,
    "oos_sharpe_v2": round(v2_oos_sharpe, 3),
    "oos_sharpe_gtaa": round(gtaa_oos_sharpe, 3),
    "oos_sharpe_ensemble_50_50": round(ensemble_sharpe, 3),
    "ensemble_dollar_since_2000": ens_dollar,
    "ensemble_max_dd_pct": ens_dd,
    "ensemble_feasible": ensemble_feasible,
    "recommendation": (
        "Register ensemble test (E12) next session — low correlation supports "
        "diversification benefit." if ensemble_feasible
        else "Ensemble not recommended — high correlation implies limited diversification."
    )
}

# ── Current portfolio mark (2026-07-14 close) ─────────────────────────────────
print("\n" + "=" * 60 + "\nPORTFOLIO MARK (2026-07-14 close)")
spy_latest = float(spy_full_bench.iloc[-1])
units = 1.333476
port_value = round(units * spy_latest, 2)
chg_dollar = round(port_value - 999.00, 2)
chg_pct = round((port_value / 999.00 - 1) * 100, 3)

# Compute v2 exposure for current date
v2_exposure = float(v2_sig_full.iloc[-1])
print(f"  SPY latest close: ${spy_latest:.2f}")
print(f"  Portfolio units: {units} SPY")
print(f"  Portfolio value: ${port_value:.2f} (chg: ${chg_dollar:+.2f}, {chg_pct:+.3f}%)")
print(f"  v2 exposure: {v2_exposure:.4f} (100% = fully invested)")

results["portfolio_mark"] = {
    "date": "2026-07-14",
    "spy_close": spy_latest,
    "units": units,
    "value": port_value,
    "chg_dollar": chg_dollar,
    "chg_pct": chg_pct,
    "v2_exposure": v2_exposure,
}

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60 + "\nSESSION 7 SUMMARY")
print(f"  E9  GEM international: {results['E9_verdict']} "
      f"(DSR={results['E9_sig']['dsr']}, "
      f"CI={results['E9_sig']['ci']}, "
      f"worstDD={results['E9_sig']['worst_dd']:.1f}%)")
print(f"  E10 GTAA-5: {results['E10_verdict']} "
      f"(DSR={results['E10_sig']['dsr']}, "
      f"CI={results['E10_sig']['ci']}, "
      f"worstDD={results['E10_sig']['worst_dd']:.1f}%)")
print(f"  E11 SectorTrend: {results['E11_verdict']} "
      f"(DSR={results['E11_sig']['dsr']}, "
      f"CI={results['E11_sig']['ci']}, "
      f"worstDD={results['E11_sig']['worst_dd']:.1f}%)")
print(f"  M1  Correlation: {corr_full:.3f} → ensemble_feasible={ensemble_feasible}")
print(f"\n  $1,000 test (2000→2026-07-14):")
for k, v in benchmarks.items():
    print(f"    {k}: ${v:,.2f}")
print(f"    v2 champion: ${v2_dollar:,.2f}")
print(f"  Portfolio mark: ${port_value:.2f} (since inception: {chg_pct:+.3f}%)")

json.dump(results, open("research/results_2026_07_15.json", "w"), indent=1)
print("\nSaved research/results_2026_07_15.json")
