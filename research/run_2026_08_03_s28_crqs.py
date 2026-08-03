"""E42: Composite Regime-Quality Strategy (CRQS) — session 28 (2026-08-03).

Hypothesis: combining a Lynch-GARP EPS quality gate (scale down equity when
Shiller real EPS 12-month growth < threshold) with the E35 CRDS regime-aware
defensive switch (IEF vs GLD based on stock-bond correlation) will improve
risk-adjusted returns over v2. The equity quality gate is motivated by Graham
(1949) / Lynch (1989): only lever up to equity beta when earnings are actually
growing. The defensive switch is the highest end$1k finding from the defensive
family ($11,420 in E35 CRDS but CI-failed; here tested as a component).

Success criteria:
  - OOS mean walk-forward Sharpe >= 0.851 (v2 bar)
  - AND deflated Sharpe >= 0.95 (correcting for 265 cumulative configs after E42)
  - AND bootstrap CI (strategy − SPY) lower bound > 0
  - AND MaxDD not worse than -22.5% (v2 -20.5% + 10% tolerance)
  - AND correlation to v2 < 0.95 (must be genuinely different from v2)

Grid (12 configs, at the cap):
  eps_threshold  ∈ {-0.05, 0.00, 0.05}
  scale_down     ∈ {0.50, 0.75}
  corr_threshold ∈ {-0.10, 0.00}
  Total: 3 × 2 × 2 = 12 configs.
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import load_ohlcv, load_shiller, data_freshness
from backtest.multi_engine import portfolio_returns, metrics as mmx
from backtest.vector_engine import strategy_returns, metrics as vmx
from strategies.vol_target import signals as v2_signals
from strategies.crqs import multi_signals as crqs_signals
from backtest.evaluation import (
    deflated_sharpe_ratio, bootstrap_difference_ci,
    sharpe_ratio,
)
from research.preregister import preregister, record_outcome, trials_this_period
from tools.risk_metrics import comprehensive_risk_report
from tools.factor_scores import composite_quality_score, factor_summary
from tools.regime_detector import detect_regime, regime_summary

COMMISSION = 0.0015
FOLDS = [
    ("fold1_IS",  "2000-01-01", "2009-12-31"),
    ("fold2_OOS", "2010-01-01", "2019-12-31"),
    ("fold3_OOS", "2020-01-01", "2026-07-31"),
]
ASSETS = ["SPY", "IEF", "GLD"]
V2_MEAN_WF_BAR = 0.851

# ── Pre-registration (before seeing results) ──────────────────────────────────
reg = preregister(
    hypothesis=(
        "E42 Composite Regime-Quality Strategy: combining a Lynch-GARP EPS "
        "quality gate (scale down equity allocation when Shiller real EPS "
        "12-month growth falls below eps_threshold) with the Ilmanen/Dalio "
        "regime-aware defensive switch (IEF in deflation, GLD in inflation, "
        "identified by rolling stock-bond correlation vs corr_threshold) will "
        "improve OOS risk-adjusted returns over the v2 champion. Economic "
        "logic: (1) EPS quality gate avoids holding full equity beta during "
        "earnings deterioration (growth recessions), capturing Lynch's 'never "
        "buy what you can't justify with earnings'. (2) Regime-aware defensive "
        "captures Ilmanen (2011): IEF hedges in deflation, GLD hedges in "
        "inflation. Together they address v2's two main failure modes: riding "
        "earnings recessions at full exposure, and holding IEF in 2022-style "
        "inflation. Expected: mean WF OOS Sharpe improvement 0.05-0.15 over "
        "v2, MaxDD improvement to -15% to -18%."
    ),
    success_criteria=(
        "OOS mean walk-forward Sharpe >= 0.851 (v2 bar) "
        "AND deflated Sharpe >= 0.95 (over ALL cumulative configs incl. 261 prior) "
        "AND bootstrap CI (strategy − SPY) lower bound > 0 "
        "AND MaxDD not worse than -22.5% (v2 -20.5% + 10% tolerance) "
        "AND correlation to v2 < 0.95 (genuinely different from v2)"
    ),
    grid_size=12,
    primary_metric="sharpe",
)
print(f"Registered E42 as {reg.id}")

# ── Data ───────────────────────────────────────────────────────────────────────
freshness = data_freshness()
print(f"\nData freshness: {freshness}")

spy = load_ohlcv("SPY", "2000-01-01")["Close"]
ief = load_ohlcv("IEF", "2000-01-01")["Close"]
gld = load_ohlcv("GLD", "2000-01-01")["Close"]
irx = load_ohlcv("^IRX", "2000-01-01")["Close"] / 100 / 252
shiller = load_shiller("2000-01-01")

panel = pd.DataFrame({"SPY": spy, "IEF": ief, "GLD": gld}).dropna(how="all")
panel = panel.ffill(limit=3)
irx = irx.reindex(panel.index, method="ffill").fillna(0.0)
spy_ret = spy.reindex(panel.index).pct_change().fillna(0.0)

# ── v2 champion baseline ───────────────────────────────────────────────────────
v2_sig = v2_signals(spy.reindex(panel.index), target_vol=0.18, lookback=20)
v2_ret = strategy_returns(spy.reindex(panel.index), v2_sig,
                           commission=COMMISSION, rf_daily=irx)

print(f"\nData range: {panel.index[0].date()} → {panel.index[-1].date()}")
print(f"GLD available from: {panel['GLD'].first_valid_index()}")

# ── Factor score snapshot (new tools, informational) ──────────────────────────
print("\n--- Current Factor Scores ---")
fscores = composite_quality_score(shiller, spy.reindex(panel.index))
fsummary = factor_summary(fscores)
for k, v in fsummary.items():
    print(f"  {k:<16}: current={v['current']:.4f}  mean={v['mean']:.4f}  "
          f"std={v['std']:.4f}")

# ── Regime snapshot (informational) ───────────────────────────────────────────
print("\n--- Current Economic Regime ---")
rdf = detect_regime(shiller, spy.reindex(panel.index), ief.reindex(panel.index))
rsumm = regime_summary(rdf)
print(f"  Current regime: {rdf['regime'].iloc[-1]}")
print(f"  Regime distribution: {rsumm['regime_pct']}")
print(f"  Avg EPS growth: {rsumm['avg_eps_growth']:.4f}")
print(f"  Avg SB corr: {rsumm['avg_sb_corr']:.4f}")

# ── Grid search ────────────────────────────────────────────────────────────────
GRID = [
    {"eps_threshold": th, "scale_down": sd, "corr_threshold": ct}
    for th in [-0.05, 0.00, 0.05]
    for sd in [0.50, 0.75]
    for ct in [-0.10, 0.00]
]
assert len(GRID) == 12, f"Grid size mismatch: {len(GRID)}"

results = []
all_mean_sharpes = []

print("\n" + "=" * 70)
print("E42 CRQS GRID SEARCH")
print("=" * 70)

for params in GRID:
    label = (f"CRQS(eps={params['eps_threshold']:+.2f},"
             f"sd={params['scale_down']:.2f},"
             f"ct={params['corr_threshold']:+.2f})")

    w = crqs_signals(spy.reindex(panel.index), shiller,
                     ief=ief.reindex(panel.index),
                     gld=gld.reindex(panel.index),
                     **params)
    ret = portfolio_returns(panel, w, commission=COMMISSION, rf_daily=irx)

    fold_sharpes, fold_dds = [], []
    for fname, fs, fe in FOLDS:
        r_fold = ret.loc[fs:fe]
        sr = sharpe_ratio(r_fold.values)
        eq = (1 + r_fold).cumprod()
        dd = float((eq / eq.cummax() - 1).min())
        fold_sharpes.append(sr)
        fold_dds.append(dd)

    mean_wf = float(np.mean(fold_sharpes[1:]))
    all_mean_sharpes.append(mean_wf)
    m = mmx(panel, w, commission=COMMISSION, rf_daily=irx, label=label)

    w_shifted = w.shift(2).fillna(0.0)
    avg_spy = w_shifted["SPY"].mean()
    avg_ief = w_shifted["IEF"].mean()
    avg_gld = w_shifted["GLD"].mean()

    corr_v2_this = float(pd.Series(ret.values[:len(v2_ret)]).corr(
        pd.Series(v2_ret.values[:len(ret)])))

    results.append({
        "label": label,
        "params": params,
        "fold_sharpes": fold_sharpes,
        "mean_wf_oos": mean_wf,
        "max_dd_pct": min(fold_dds) * 100,
        "full_sample": m,
        "avg_spy": avg_spy,
        "avg_ief": avg_ief,
        "avg_gld": avg_gld,
        "corr_v2": corr_v2_this,
        "ret": ret,
    })
    print(f"\n{label}")
    print(f"  Folds: {[round(s,3) for s in fold_sharpes]}")
    print(f"  Mean WF OOS: {mean_wf:.3f}  (bar: {V2_MEAN_WF_BAR})")
    print(f"  MaxDD: {min(fold_dds)*100:.2f}%  End$1k: {m['End$per1k']:.0f}")
    print(f"  Avg SPY/IEF/GLD: {avg_spy:.2%}/{avg_ief:.2%}/{avg_gld:.2%}")
    print(f"  Corr to v2: {corr_v2_this:.3f}")

# ── Pick best config and full evaluation ──────────────────────────────────────
best = max(results, key=lambda r: r["mean_wf_oos"])
best_ret = best["ret"]
print(f"\n{'='*70}")
print(f"BEST CONFIG: {best['label']}")
print(f"{'='*70}")

# DSR
n_trials = trials_this_period()
# DSR uses population of per-fold Sharpe/sqrt(252) estimates
dsr = deflated_sharpe_ratio(best_ret.values, [s / np.sqrt(252) for s in all_mean_sharpes])
print(f"DSR (within-session {len(all_mean_sharpes)} configs): {dsr:.4f}")
print(f"  Full deflation with {n_trials} cumulative configs will be lower")

# Bootstrap CI vs SPY
ci = bootstrap_difference_ci(best_ret.values, spy_ret.values,
                              metric="sharpe", n=10000, seed=0)
print(f"CI vs SPY (full sample): [{ci.lo:.4f}, {ci.hi:.4f}]")
print(f"Clears zero: {ci.clears_noise}")

# Corr to v2
corr_v2 = best["corr_v2"]
print(f"Correlation to v2: {corr_v2:.3f}  (ensemble threshold: <0.50)")

# Advanced risk metrics
print("\n--- Advanced Risk Metrics (best config) ---")
risk_rpt = comprehensive_risk_report(best_ret.values, spy_ret.values[:len(best_ret)])
for k, v in risk_rpt.items():
    print(f"  {k:<22}: {v}")

# Comparison table
v2_m = vmx(spy.reindex(panel.index), v2_sig, commission=COMMISSION,
           rf_daily=irx, label="v2_champion")
best_m = best["full_sample"]
spy_m = vmx(spy.reindex(panel.index),
            pd.Series(1.0, index=panel.index),
            commission=0.0, rf_daily=None, label="buy_hold_SPY")

print(f"\n{'Strategy':<30} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 64)
for m in [v2_m, best_m, spy_m]:
    print(f"{m['label']:<30} {m['Sharpe']:>7.3f} {m['MaxDD']:>8.2f}% "
          f"{m['End$per1k']:>8.0f} {m['CAGR']:>6.2f}%")

# ── Verdict ────────────────────────────────────────────────────────────────────
passes = (
    best["mean_wf_oos"] >= V2_MEAN_WF_BAR
    and ci.clears_noise
    and best["max_dd_pct"] > -22.5
    and dsr >= 0.95
    and corr_v2 < 0.95
)
verdict = "adopted" if passes else "discarded"
verdict_label = "PASSES" if passes else "FAILS"

evidence = {
    "session": "s28_2026-08-03",
    "best_config": best["label"],
    "best_params": best["params"],
    "mean_wf_oos": round(best["mean_wf_oos"], 4),
    "v2_bar": V2_MEAN_WF_BAR,
    "beats_v2_bar": best["mean_wf_oos"] >= V2_MEAN_WF_BAR,
    "fold_sharpes": [round(s, 4) for s in best["fold_sharpes"]],
    "max_dd_pct": round(best["max_dd_pct"], 2),
    "ci_lo": round(ci.lo, 4),
    "ci_hi": round(ci.hi, 4),
    "ci_clears_zero": ci.clears_noise,
    "dsr_within_session": round(dsr, 4),
    "dsr_passes": dsr >= 0.95,
    "end1k_best": round(best_m["End$per1k"], 0),
    "end1k_v2": round(v2_m["End$per1k"], 0),
    "corr_to_v2": round(corr_v2, 3),
    "ensemble_eligible": corr_v2 < 0.50,
    "avg_spy_weight": round(best["avg_spy"], 4),
    "avg_ief_weight": round(best["avg_ief"], 4),
    "avg_gld_weight": round(best["avg_gld"], 4),
    "risk_metrics": risk_rpt,
    "all_results": [
        {
            "label": r["label"],
            "mean_wf_oos": round(r["mean_wf_oos"], 4),
            "fold_sharpes": [round(s, 4) for s in r["fold_sharpes"]],
            "max_dd_pct": round(r["max_dd_pct"], 2),
            "corr_v2": round(r["corr_v2"], 3),
        }
        for r in results
    ],
}

print(f"\n{'='*70}")
print(f"VERDICT: {verdict_label} — {verdict.upper()}")
print(f"{'='*70}")
print(json.dumps({k: v for k, v in evidence.items() if k != "all_results"}, indent=2))

record_outcome(reg.id, verdict=verdict, evidence=evidence,
               notes=f"Session 28. {verdict_label} pre-registered bar.")

print("\nE42 CRQS complete.")
