"""E43: Fractional Kelly CRQS — session 29 (2026-08-04).

Hypothesis: The vol_target=0.18 in the best CRQS config corresponds to a specific
implied Kelly fraction. Testing different vol_targets (as different Kelly fractions)
will reveal whether the current 17.3%-of-full-Kelly position is optimal for
geometric growth, or whether a different Kelly fraction improves risk-adjusted returns.

Expected: configs near vol_target=0.18 will have near-identical CI (the strategy
is already at 1.0 exposure most of the time). Lower vol_targets may reduce DD at
the cost of terminal value. The experiment quantifies this tradeoff explicitly
in Kelly terms.
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
from strategies.kelly_sized_crqs import multi_signals as kelly_crqs_signals, VOL_TARGET_GRID
from backtest.evaluation import (
    deflated_sharpe_ratio, bootstrap_difference_ci, sharpe_ratio,
)
from research.preregister import preregister, record_outcome, trials_this_period
from tools.kelly import kelly_summary, vol_target_to_kelly_equiv

COMMISSION = 0.0015
FOLDS = [
    ("fold1_IS",  "2000-01-01", "2009-12-31"),
    ("fold2_OOS", "2010-01-01", "2019-12-31"),
    ("fold3_OOS", "2020-01-01", "2026-08-03"),
]
V2_MEAN_WF_BAR   = 0.851
CRQS_MEAN_WF_BAR = 1.033   # CRQS champion bar
ASSETS = ["SPY", "IEF", "GLD"]

# ── Pre-registration ─────────────────────────────────────────────────────────
reg = preregister(
    hypothesis=(
        "E43 Fractional Kelly CRQS: The CRQS champion (eps=0.00, sd=0.75, "
        "ct=0.00) uses vol_target=0.18, implying ~17.3% of full Kelly fraction "
        "(full Kelly = Sharpe/sigma = 0.960/0.107 ≈ 8.97×, capped at 1.0). "
        "Testing vol_target ∈ {0.09, 0.12, 0.15, 0.18, 0.21, 0.24} will show "
        "whether lower vol_targets (more conservative Kelly fractions) improve "
        "geometric growth via variance reduction, or whether the current 0.18 "
        "is already near-optimal under the no-leverage constraint. Informed by "
        "Thorp (2008) and Haghani-Dewey (2016): at a Kelly fraction well below "
        "full Kelly, reducing further should decrease geometric growth. Expected "
        "outcome: DISCARDED — all configs near vol_target=0.18 produce near- "
        "identical CI; the CI may still straddle zero since CRQS (E42) already "
        "cleared it at vol_target=0.18."
    ),
    success_criteria=(
        "Mean WF OOS Sharpe >= 1.033 (CRQS bar) for the best Kelly-fraction config "
        "AND bootstrap CI lower bound > 0 AND MaxDD not worse than -22.5% "
        "AND improvement vs CRQS vol=0.18 is statistically meaningful (CI lower bound "
        "of config - vol_0.18 is > 0)."
    ),
    grid_size=6,
    primary_metric="sharpe",
)
print(f"Registered E43 as {reg.id}")

# ── Data ─────────────────────────────────────────────────────────────────────
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

# ── Kelly analysis on CRQS champion ──────────────────────────────────────────
CRQS_SHARPE = 0.960
CRQS_SIGMA  = 0.107
ks = kelly_summary(CRQS_SHARPE, CRQS_SIGMA)
print("\n--- Kelly Analysis for CRQS Champion ---")
print(f"  Full Kelly: {ks['full_kelly']:.2f}× (capped at {ks['leverage_cap']:.1f}×)")
for name, v in ks['fractions'].items():
    print(f"  {name:8s}: position={v['position']:.4f}  g_ann={v['growth_rate_ann']:.2f}%")
print("\n  Kelly equivalents of each vol_target:")
for vt in VOL_TARGET_GRID:
    k_eq = vol_target_to_kelly_equiv(vt, CRQS_SHARPE)
    print(f"    vol_target={vt:.2f}  →  implied Kelly fraction = {k_eq:.4f} "
          f"({k_eq*100:.1f}% of full Kelly)")

# ── v2 baseline ───────────────────────────────────────────────────────────────
v2_sig = v2_signals(spy.reindex(panel.index), target_vol=0.18, lookback=20)
v2_ret = strategy_returns(spy.reindex(panel.index), v2_sig,
                          commission=COMMISSION, rf_daily=irx)

# ── Grid search ──────────────────────────────────────────────────────────────
results = []
all_mean_sharpes = []

print("\n" + "=" * 70)
print("E43 FRACTIONAL KELLY CRQS GRID SEARCH")
print("=" * 70)

for vt in VOL_TARGET_GRID:
    label = f"KellyCRQS(vt={vt:.2f})"
    k_eq = vol_target_to_kelly_equiv(vt, CRQS_SHARPE)

    w = kelly_crqs_signals(spy.reindex(panel.index), shiller,
                           ief=ief.reindex(panel.index),
                           gld=gld.reindex(panel.index),
                           vol_target=vt, lookback=20)
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

    corr_v2 = float(pd.Series(ret.values[:len(v2_ret)]).corr(
        pd.Series(v2_ret.values[:len(ret)])))

    results.append({
        "label": label,
        "vol_target": vt,
        "kelly_equiv": k_eq,
        "fold_sharpes": fold_sharpes,
        "mean_wf_oos": mean_wf,
        "max_dd_pct": min(fold_dds) * 100,
        "full_sample": m,
        "corr_v2": corr_v2,
        "ret": ret,
    })

    print(f"\n{label}  (Kelly equiv: {k_eq:.4f} = {k_eq*100:.1f}%)")
    print(f"  Folds: {[round(s,3) for s in fold_sharpes]}")
    print(f"  Mean WF OOS: {mean_wf:.3f}  MaxDD: {min(fold_dds)*100:.2f}%  "
          f"End$1k: {m['End$per1k']:.0f}")
    print(f"  Corr to v2: {corr_v2:.3f}")

# ── Best config evaluation ────────────────────────────────────────────────────
best = max(results, key=lambda r: r["mean_wf_oos"])
best_ret = best["ret"]
n_trials = trials_this_period()
dsr = deflated_sharpe_ratio(best_ret.values,
                             [s / np.sqrt(252) for s in all_mean_sharpes])
ci = bootstrap_difference_ci(best_ret.values, spy_ret.values,
                              metric="sharpe", n=10000, seed=0)

print(f"\n{'='*70}")
print(f"BEST CONFIG: {best['label']}")
print(f"DSR: {dsr:.4f}  CI vs SPY: [{ci.lo:.4f}, {ci.hi:.4f}]  Clears: {ci.clears_noise}")
print(f"Kelly equiv: {best['kelly_equiv']:.4f} ({best['kelly_equiv']*100:.1f}% of full Kelly)")

# Comparison table
crqs_w = kelly_crqs_signals(spy.reindex(panel.index), shiller,
                             ief=ief.reindex(panel.index),
                             gld=gld.reindex(panel.index),
                             vol_target=0.18, lookback=20)
crqs_ret = portfolio_returns(panel, crqs_w, commission=COMMISSION, rf_daily=irx)
crqs_m = mmx(panel, crqs_w, commission=COMMISSION, rf_daily=irx, label="CRQS(vt=0.18) champion")
v2_m = vmx(spy.reindex(panel.index), v2_sig, commission=COMMISSION,
           rf_daily=irx, label="v2_champion")
spy_m = vmx(spy.reindex(panel.index),
            pd.Series(1.0, index=panel.index),
            commission=0.0, rf_daily=None, label="buy_hold_SPY")

print(f"\n{'Strategy':<35} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 70)
for row in [crqs_m, best["full_sample"], v2_m, spy_m]:
    print(f"{row['label']:<35} {row['Sharpe']:>7.3f} {row['MaxDD']:>8.2f}% "
          f"{row['End$per1k']:>8.0f} {row['CAGR']:>6.2f}%")

# ── Verdict ───────────────────────────────────────────────────────────────────
passes = (
    best["mean_wf_oos"] >= CRQS_MEAN_WF_BAR
    and ci.clears_noise
    and best["max_dd_pct"] > -22.5
    and dsr >= 0.95
)
verdict = "adopted" if passes else "discarded"

evidence = {
    "session": "s29_2026-08-04",
    "experiment": "E43_kelly_crqs",
    "best_config": best["label"],
    "best_vol_target": best["vol_target"],
    "best_kelly_equiv": round(best["kelly_equiv"], 4),
    "full_kelly": round(ks["full_kelly"], 4),
    "mean_wf_oos": round(best["mean_wf_oos"], 4),
    "max_dd_pct": round(best["max_dd_pct"], 2),
    "dsr": round(dsr, 4),
    "ci_lo": round(ci.lo, 4),
    "ci_hi": round(ci.hi, 4),
    "ci_clears_zero": ci.clears_noise,
    "all_configs": [
        {"label": r["label"], "vol_target": r["vol_target"],
         "kelly_equiv": round(r["kelly_equiv"], 4),
         "mean_wf_oos": round(r["mean_wf_oos"], 4),
         "max_dd_pct": round(r["max_dd_pct"], 2)}
        for r in results
    ],
}

print(f"\nVERDICT: {'PASSES' if passes else 'FAILS'} → {verdict.upper()}")
record_outcome(reg.id, verdict=verdict, evidence=evidence,
               notes=f"Session 29. {verdict.upper()}.")
print("\nE43 complete.")
