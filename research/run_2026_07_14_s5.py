"""Session 2026-07-14 s5: Investing philosophy expansion.

Experiments (ROADMAP items 1, 2, 4):
  E3 — Dual Momentum (Antonacci 2014): absolute + relative momentum on
       SPY/QQQ/DIA equity universe, TLT as defensive harbor.
       Grid: lookback {231,252,273} × skip {0,21} = 6 configs.
  E4 — Drawdown Kill-Switch overlay on frozen v2 champion:
       go-to-cash below DD threshold, re-enter at recovery.
       Grid: kill_dd {-0.12,-0.15} × recovery {-0.06,-0.08} = 4 configs.
  E5 — Cross-Sectional Sector Momentum: top-N sectors by 12-1 month
       momentum equally weighted.
       Grid: lookback {231,252} × top_n {3,4} = 4 configs.

Pre-registration is done BEFORE any results are seen (enforced by preregister()).
Protocol: walk-forward folds 2000-09 / 2010-19 / 2020-25H; LOCKED HOLDOUT
2025-07-14 onward; costs 0.15%. All multi-asset strategies use multi_engine.py.

$1,000 paper test (required by session spec): terminal value of each strategy
vs SPY, DIA, QQQ, Mag-7 over the full 2000-2026-07-13 walk-forward window.
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, sma_trend, dual_momentum, drawdown_kill, sector_momentum
from research.preregister import preregister, record_outcome, trials_this_period

# ── Constants ────────────────────────────────────────────────────────────────
HOLDOUT_START = "2025-07-14"
COST = 0.0015
FOLDS = [
    ("2000-2009",   "2000-01-01", "2009-12-31"),
    ("2010-2019",   "2010-01-01", "2019-12-31"),
    ("2020-2025H",  "2020-01-01", "2025-07-11"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-11"    # primary OOS fold for significance

# ── Data ──────────────────────────────────────────────────────────────────────
freshness = loader.data_freshness()
print(f"Data freshness: {freshness}")

spy_full = loader.load_ohlcv("SPY")["Close"]
spy = spy_full[spy_full.index < HOLDOUT_START]

irx = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily = (irx / 100.0) / 252.0

# Multi-asset panel (exclude holdout)
UNIVERSE = ["SPY", "QQQ", "DIA", "TLT", "IEF", "SHY", "GLD", "IWM",
            "XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLU","XLB","XLRE","XLC",
            "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"]
panel_full = loader.load_universe(UNIVERSE)
panel = panel_full[panel_full.index < HOLDOUT_START]

print(f"SPY: {len(spy)} rows, {spy.index[0].date()} -> {spy.index[-1].date()}")
print(f"Panel: {panel.shape}, tickers: {list(panel.columns)}")

# ── Pre-registration (BEFORE seeing results) ──────────────────────────────────
prior_trials = trials_this_period()
print(f"\nPrior total configs registered: {prior_trials}")

reg_e3 = preregister(
    hypothesis=(
        "Antonacci (2014) Dual Momentum combining absolute momentum (best equity "
        "vs SHY T-bill bar) and relative momentum (SPY/QQQ/DIA) with TLT as "
        "defensive harbor achieves OOS deflated-Sharpe >= 0.95 for 6 trials, "
        "and bootstrap diff-vs-SPY Sharpe CI excluding zero on 2020-2025H fold."
    ),
    success_criteria=(
        "DSR >= 0.95 (penalized for 6 configs) AND bootstrap diff-vs-SPY CI "
        "lower bound > 0.0 on 2020-2025H AND worst-fold MaxDD <= -30% "
        "(looser than v2 because TLT acts as defensive harbor in bear markets)."
    ),
    grid_size=6,
    primary_metric="sharpe",
)
reg_e4 = preregister(
    hypothesis=(
        "A drawdown kill-switch overlay on frozen v2 (go-to-cash at kill_dd, "
        "re-enter at recovery_dd) reduces worst-fold MaxDD by >= 2pp without "
        "dropping any single-fold Sharpe by > 0.08 relative to v2 baseline."
    ),
    success_criteria=(
        "worst-fold MaxDD improves >= 2pp vs v2 AND no single fold Sharpe "
        "drops > 0.08 AND DSR >= 0.95 for 4 configs."
    ),
    grid_size=4,
    primary_metric="sharpe",
)
reg_e5 = preregister(
    hypothesis=(
        "Cross-sectional momentum on S&P sector ETFs (top-N by 12-1 month "
        "momentum, equal-weight) achieves OOS deflated-Sharpe >= 0.95 for "
        "4 trials and bootstrap diff-vs-SPY CI excluding zero on 2020-2025H."
    ),
    success_criteria=(
        "DSR >= 0.95 AND diff-vs-SPY CI lower bound > 0.0 on 2020-2025H "
        "AND worst-fold MaxDD <= -35% (sector strategies carry more idiosyncratic DD)."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

print(f"\nRegistered: E3={reg_e3.id} E4={reg_e4.id} E5={reg_e5.id}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def single_fold_sharpes(sig, cost=COST):
    """Walk-forward Sharpes for a single-asset (SPY) signal."""
    return [ve.metrics(spy.loc[a:b], sig.loc[a:b], cost, rf_daily.loc[a:b])["Sharpe"]
            for _, a, b in FOLDS]

def multi_fold_sharpes(weights, price_pan, cost=COST):
    """Walk-forward Sharpes for a multi-asset weight schedule."""
    rows = []
    for _, a, b in FOLDS:
        pan_f = price_pan.loc[a:b]
        w_f = weights.loc[a:b]
        sr = me.portfolio_returns(pan_f, w_f, cost, rf_daily.loc[a:b])
        r = sr[sr.index > sr.index[0]]
        sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0
        rows.append(round(float(sh), 3))
    return rows

def multi_fold_metrics(weights, price_pan, label, cost=COST):
    """Full fold-level metrics for a multi-asset strategy."""
    rows = []
    for name, a, b in FOLDS:
        m = me.metrics(price_pan.loc[a:b], weights.loc[a:b], cost, rf_daily.loc[a:b],
                       f"{label} {name}")
        rows.append(m)
    return rows

def multi_oos_returns(weights, price_pan, cost=COST):
    """Return series on the OOS fold for significance testing."""
    sr = me.portfolio_returns(price_pan.loc[OOS_A:OOS_B],
                              weights.loc[OOS_A:OOS_B], cost,
                              rf_daily.loc[OOS_A:OOS_B])
    return sr[sr.index > sr.index[0]]

def spy_oos_returns():
    """SPY B&H return series on the OOS fold (for bootstrap reference)."""
    c = spy.loc[OOS_A:OOS_B]
    return c.pct_change().fillna(0.0)[1:]

# ── Baselines (v1, v2, SPY B&H) ──────────────────────────────────────────────
v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
v2_wf_sharpes = single_fold_sharpes(v2)
print(f"\n[BASELINE] v2 WF Sharpes: {v2_wf_sharpes}, mean={np.mean(v2_wf_sharpes):.3f}")

results = {
    "session": "2026-07-14-s5",
    "data_freshness": freshness,
    "v2_baseline_wf_sharpes": v2_wf_sharpes,
    "E3": [],
    "E4": [],
    "E5": [],
    "dollar_test": {},
}

# ── E3: Dual Momentum ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("E3: Dual Momentum (Antonacci)")

e3_configs = [
    {"lookback": lb, "skip": sk}
    for lb in [231, 252, 273]
    for sk in [0, 21]
]
e3_all_sharpes = []

for cfg in e3_configs:
    w = dual_momentum.multi_signals(panel, **cfg)
    sh = multi_fold_sharpes(w, panel)
    e3_all_sharpes.extend(sh)
    mm = multi_fold_metrics(w, panel, f"DualMom lb{cfg['lookback']} sk{cfg['skip']}")
    entry = {"cfg": cfg, "wf_sharpes": sh, "mean": round(np.mean(sh), 3), "folds": mm}
    results["E3"].append(entry)
    print(f"  lookback={cfg['lookback']} skip={cfg['skip']}: WF={sh} mean={entry['mean']:.3f}")

# Best config by mean WF Sharpe
best_e3 = max(results["E3"], key=lambda d: d["mean"])
print(f"\n  Best E3 config: {best_e3['cfg']} mean={best_e3['mean']:.3f}")

# Statistical evaluation on best config
best_w_e3 = dual_momentum.multi_signals(panel, **best_e3["cfg"])
r_e3 = multi_oos_returns(best_w_e3, panel)
r_spy = spy_oos_returns()

dsr_e3 = ev.deflated_sharpe_ratio(r_e3.values, e3_all_sharpes)
ci_e3 = ev.bootstrap_difference_ci(r_e3.values, r_spy.reindex(r_e3.index).values)
worst_dd_e3 = min(f["MaxDD"] for f in best_e3["folds"])

results["E3_sig"] = {
    "best_cfg": best_e3["cfg"],
    "mean_wf_sharpe": best_e3["mean"],
    "worst_fold_dd": worst_dd_e3,
    "dsr": round(dsr_e3, 4),
    "ci_vs_spy": ci_e3.__dict__,
    "pass_dsr": dsr_e3 >= 0.95,
    "pass_ci": ci_e3.lo > 0.0,
    "pass_dd": worst_dd_e3 >= -30.0,
}
verdict_e3 = "adopted" if (results["E3_sig"]["pass_dsr"] and
                           results["E3_sig"]["pass_ci"] and
                           results["E3_sig"]["pass_dd"]) else "discarded"
record_outcome(reg_e3.id, verdict=verdict_e3,
               evidence=results["E3_sig"], notes=f"Session s5 E3 {verdict_e3}")
print(f"  DSR={dsr_e3:.4f} CI_lo={ci_e3.lo:.3f} CI_hi={ci_e3.hi:.3f} worst_DD={worst_dd_e3}")
print(f"  VERDICT E3: {verdict_e3.upper()}")

# ── E4: Drawdown Kill-Switch on v2 ───────────────────────────────────────────
print("\n" + "="*60)
print("E4: Drawdown Kill-Switch overlay on v2")

e4_configs = [
    {"kill_dd": kd, "recovery_dd": rd}
    for kd in [-0.12, -0.15]
    for rd in [-0.06, -0.08]
]
e4_all_sharpes = []
v2_worst_dd = min(ve.metrics(spy.loc[a:b], v2.loc[a:b], COST, rf_daily.loc[a:b])["MaxDD"]
                  for _, a, b in FOLDS)

for cfg in e4_configs:
    sig = drawdown_kill.overlay_signals(v2, spy, commission=COST, **cfg)
    sh = single_fold_sharpes(sig)
    e4_all_sharpes.extend(sh)
    fold_metrics = []
    for name, a, b in FOLDS:
        m = ve.metrics(spy.loc[a:b], sig.loc[a:b], COST, rf_daily.loc[a:b],
                       f"v2+kill kd{cfg['kill_dd']} rec{cfg['recovery_dd']} {name}")
        fold_metrics.append(m)
    worst_dd = min(m["MaxDD"] for m in fold_metrics)
    entry = {
        "cfg": cfg, "wf_sharpes": sh, "mean": round(np.mean(sh), 3),
        "worst_dd": worst_dd, "folds": fold_metrics,
    }
    results["E4"].append(entry)
    print(f"  kill={cfg['kill_dd']} rec={cfg['recovery_dd']}: "
          f"WF={sh} mean={entry['mean']:.3f} worstDD={worst_dd:.2f}")

# Best config by mean WF Sharpe
best_e4 = max(results["E4"], key=lambda d: d["mean"])
print(f"\n  Best E4 config: {best_e4['cfg']} mean={best_e4['mean']:.3f}")

# Statistical evaluation on best config
sig_e4_best = drawdown_kill.overlay_signals(v2, spy, commission=COST, **best_e4["cfg"])
r_e4 = ve.strategy_returns(spy, sig_e4_best, COST, rf_daily).loc[OOS_A:OOS_B]
r_e4 = r_e4[r_e4.index > r_e4.index[0]]

dsr_e4 = ev.deflated_sharpe_ratio(r_e4.values, e4_all_sharpes)
ci_e4_vs_spy = ev.bootstrap_difference_ci(r_e4.values, r_spy.reindex(r_e4.index).values)
r_v2_oos = ve.strategy_returns(spy, v2, COST, rf_daily).loc[OOS_A:OOS_B][1:]
ci_e4_vs_v2 = ev.bootstrap_difference_ci(r_e4.values, r_v2_oos.reindex(r_e4.index).values)

# Per-fold Sharpe comparison: v2 vs best kill
v2_fold_sharpes = single_fold_sharpes(v2)
max_sharpe_drop = max(v2_fold_sharpes[i] - best_e4["wf_sharpes"][i]
                      for i in range(len(FOLDS)))
dd_improvement = best_e4["worst_dd"] - v2_worst_dd  # should be positive (less negative)

results["E4_sig"] = {
    "best_cfg": best_e4["cfg"],
    "mean_wf_sharpe": best_e4["mean"],
    "v2_mean_sharpe": round(np.mean(v2_fold_sharpes), 3),
    "worst_dd_kill": best_e4["worst_dd"],
    "worst_dd_v2": v2_worst_dd,
    "dd_improvement_pp": round(dd_improvement, 2),
    "max_fold_sharpe_drop": round(max_sharpe_drop, 3),
    "dsr": round(dsr_e4, 4),
    "ci_vs_spy": ci_e4_vs_spy.__dict__,
    "ci_vs_v2": ci_e4_vs_v2.__dict__,
    "pass_dd": dd_improvement >= 2.0,
    "pass_sharpe_drop": max_sharpe_drop <= 0.08,
    "pass_dsr": dsr_e4 >= 0.95,
}
verdict_e4 = "adopted" if (results["E4_sig"]["pass_dd"] and
                            results["E4_sig"]["pass_sharpe_drop"] and
                            results["E4_sig"]["pass_dsr"]) else "discarded"
record_outcome(reg_e4.id, verdict=verdict_e4,
               evidence=results["E4_sig"], notes=f"Session s5 E4 {verdict_e4}")
print(f"  DD improvement: {dd_improvement:+.2f}pp vs v2 (need >=2pp)")
print(f"  Max fold Sharpe drop: {max_sharpe_drop:.3f} (need <=0.08)")
print(f"  DSR={dsr_e4:.4f}")
print(f"  VERDICT E4: {verdict_e4.upper()}")

# ── E5: Cross-Sectional Sector Momentum ──────────────────────────────────────
print("\n" + "="*60)
print("E5: Cross-Sectional Sector Momentum")

e5_configs = [
    {"lookback": lb, "top_n": n}
    for lb in [231, 252]
    for n in [3, 4]
]
e5_all_sharpes = []

for cfg in e5_configs:
    w = sector_momentum.multi_signals(panel, **cfg)
    sh = multi_fold_sharpes(w, panel)
    e5_all_sharpes.extend(sh)
    mm = multi_fold_metrics(w, panel, f"SectorMom lb{cfg['lookback']} top{cfg['top_n']}")
    entry = {"cfg": cfg, "wf_sharpes": sh, "mean": round(np.mean(sh), 3), "folds": mm}
    results["E5"].append(entry)
    print(f"  lookback={cfg['lookback']} top_n={cfg['top_n']}: "
          f"WF={sh} mean={entry['mean']:.3f}")

best_e5 = max(results["E5"], key=lambda d: d["mean"])
print(f"\n  Best E5 config: {best_e5['cfg']} mean={best_e5['mean']:.3f}")

# Statistical evaluation on best config
best_w_e5 = sector_momentum.multi_signals(panel, **best_e5["cfg"])
r_e5 = multi_oos_returns(best_w_e5, panel)

dsr_e5 = ev.deflated_sharpe_ratio(r_e5.values, e5_all_sharpes)
ci_e5 = ev.bootstrap_difference_ci(r_e5.values, r_spy.reindex(r_e5.index).values)
worst_dd_e5 = min(f["MaxDD"] for f in best_e5["folds"])

results["E5_sig"] = {
    "best_cfg": best_e5["cfg"],
    "mean_wf_sharpe": best_e5["mean"],
    "worst_fold_dd": worst_dd_e5,
    "dsr": round(dsr_e5, 4),
    "ci_vs_spy": ci_e5.__dict__,
    "pass_dsr": dsr_e5 >= 0.95,
    "pass_ci": ci_e5.lo > 0.0,
    "pass_dd": worst_dd_e5 >= -35.0,
}
verdict_e5 = "adopted" if (results["E5_sig"]["pass_dsr"] and
                           results["E5_sig"]["pass_ci"] and
                           results["E5_sig"]["pass_dd"]) else "discarded"
record_outcome(reg_e5.id, verdict=verdict_e5,
               evidence=results["E5_sig"], notes=f"Session s5 E5 {verdict_e5}")
print(f"  DSR={dsr_e5:.4f} CI_lo={ci_e5.lo:.3f} CI_hi={ci_e5.hi:.3f} worst_DD={worst_dd_e5}")
print(f"  VERDICT E5: {verdict_e5.upper()}")

# ── $1,000 Paper Test (Full Walk-Forward, 2000-2026-07-13) ───────────────────
print("\n" + "="*60)
print("$1,000 Paper Test: terminal values 2000-01-03 -> 2026-07-13")

FULL_A, FULL_B = "2000-01-01", spy.index[-1].strftime("%Y-%m-%d")

def terminal_single(sig, label):
    """Terminal $1k value for a single-asset SPY strategy."""
    c = spy.loc[FULL_A:FULL_B]
    s = sig.loc[FULL_A:FULL_B]
    m = ve.metrics(c, s, COST, rf_daily.loc[FULL_A:FULL_B], label)
    return m

def terminal_multi(weights, pan, label):
    """Terminal $1k value for a multi-asset strategy."""
    p = pan.loc[FULL_A:FULL_B]
    w = weights.loc[FULL_A:FULL_B]
    m = me.metrics(p, w, COST, rf_daily.loc[FULL_A:FULL_B], label)
    return m

def terminal_bh(close, label):
    """B&H terminal metrics on a price series."""
    c = close.loc[FULL_A:FULL_B].dropna()
    sig = pd.Series(1.0, index=c.index)
    m = ve.metrics(c, sig, 0.0, None, label)
    return m

# Build strategies for full period
v2_full = vol_target.signals(spy.loc[FULL_A:FULL_B], target_vol=0.18, lookback=20)
panel_full_period = panel_full.loc[FULL_A:FULL_B]

dollar_test = {}
dollar_test["v2_champion"] = terminal_single(v2_full, "v2 champion")

# E3 result (use best config regardless of verdict — show the number)
w_e3_full = dual_momentum.multi_signals(panel_full_period, **best_e3["cfg"])
dollar_test["dual_momentum"] = terminal_multi(w_e3_full, panel_full_period, "Dual Momentum")

# E4 result
sig_e4_full = drawdown_kill.overlay_signals(
    vol_target.signals(spy.loc[FULL_A:FULL_B], target_vol=0.18, lookback=20),
    spy.loc[FULL_A:FULL_B], commission=COST, **best_e4["cfg"]
)
dollar_test["v2_kill_switch"] = terminal_single(sig_e4_full, "v2+Kill Switch")

# E5 result
w_e5_full = sector_momentum.multi_signals(panel_full_period, **best_e5["cfg"])
dollar_test["sector_momentum"] = terminal_multi(w_e5_full, panel_full_period, "Sector Momentum")

# Benchmarks
dollar_test["SPY_BH"] = terminal_bh(spy.loc[FULL_A:FULL_B], "SPY B&H")
dollar_test["DIA_BH"] = terminal_bh(panel_full_period.get("DIA", pd.Series(dtype=float)), "DIA (DOW) B&H")
dollar_test["QQQ_BH"] = terminal_bh(panel_full_period.get("QQQ", pd.Series(dtype=float)), "QQQ B&H")
mag7_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
mag7_avail = [t for t in mag7_tickers if t in panel_full_period.columns]
if mag7_avail:
    mag7_r = panel_full_period[mag7_avail].pct_change().mean(axis=1, skipna=True).fillna(0.0)
    mag7_px = 100 * (1 + mag7_r).cumprod()
    dollar_test["Mag7_eqw"] = terminal_bh(mag7_px, "Mag-7 eqw B&H")

results["dollar_test"] = dollar_test

print("\n  Strategy                | CAGR% | Sharpe | MaxDD%  | End $1k")
print("  " + "-"*62)
for k, m in dollar_test.items():
    if isinstance(m, dict) and "CAGR" in m:
        print(f"  {m['label']:<22} | {m['CAGR']:>5.1f} | {m['Sharpe']:>6.3f} | "
              f"{m['MaxDD']:>7.1f} | ${m['End$per1k']:>8,.0f}")

# ── Save results ─────────────────────────────────────────────────────────────
out_path = "research/results_2026_07_14_s5.json"
json.dump(results, open(out_path, "w"), indent=1, default=str)
print(f"\nResults saved to {out_path}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SESSION S5 SUMMARY")
print(f"  E3 Dual Momentum:       {verdict_e3.upper()} (DSR={results['E3_sig']['dsr']:.4f})")
print(f"  E4 Kill-Switch on v2:   {verdict_e4.upper()} (DSR={results['E4_sig']['dsr']:.4f})")
print(f"  E5 Sector Momentum:     {verdict_e5.upper()} (DSR={results['E5_sig']['dsr']:.4f})")
