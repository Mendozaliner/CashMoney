"""E44: CRQS + MinVar Ensemble — session 29 (2026-08-04).

Hypothesis: Blending CRQS (Sharpe 0.960, corr_v2=0.923) with MinVar
(mean_wf ~0.887, corr_v2=0.267, all-time record low correlation) will
produce a portfolio with better risk-adjusted returns than CRQS alone,
because the two strategies have a cross-correlation of approximately
0.267 × 0.923 ≈ 0.246, providing substantial diversification benefit.

Pre-condition met: Criterion-1 significance (CRQS CI [+0.048, +0.864])
is now satisfied, allowing ensemble investigation.

Challenge: MinVar end$1k = $3,251 vs CRQS $12,104 — the IEF-heavy
allocation in MinVar costs significant return in bull markets. Any blend
weight drags terminal value. The experiment quantifies whether the
Sharpe improvement justifies the return sacrifice.
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
from strategies.min_var import multi_signals as minvar_signals
from strategies.crqs_minvar_ensemble import multi_signals as ensemble_signals, BLEND_GRID
from backtest.evaluation import (
    deflated_sharpe_ratio, bootstrap_difference_ci, sharpe_ratio,
)
from research.preregister import preregister, record_outcome, trials_this_period

COMMISSION = 0.0015
FOLDS = [
    ("fold1_IS",  "2000-01-01", "2009-12-31"),
    ("fold2_OOS", "2010-01-01", "2019-12-31"),
    ("fold3_OOS", "2020-01-01", "2026-08-03"),
]
CRQS_MEAN_WF_BAR = 1.033
ASSETS = ["SPY", "IEF", "GLD"]

# ── Pre-registration ─────────────────────────────────────────────────────────
reg = preregister(
    hypothesis=(
        "E44 CRQS+MinVar Ensemble: Blending the CRQS champion (mean_wf=1.033, "
        "corr_v2=0.923) with the MinVar portfolio (mean_wf≈0.887, corr_v2=0.267) "
        "across blend_w ∈ {0.95, 0.90, 0.80, 0.70, 0.60} CRQS weight will produce "
        "superior risk-adjusted returns via diversification. Theoretical basis: "
        "estimated CRQS-MinVar correlation ≈ 0.246 (product of individual corr_v2s). "
        "Portfolio theory (Markowitz 1952) predicts optimal blend ≈ 80-90% CRQS "
        "given large Sharpe differential. Expected outcome: DISCARDED — MinVar's "
        "severe raw-return deficit ($3,251 vs $12,104 per $1k) will drag any blend "
        "below CRQS's CI lower bound; the 5-year OOS window lacks enough bear-market "
        "draws to demonstrate the diversification benefit statistically."
    ),
    success_criteria=(
        "Best ensemble mean WF OOS Sharpe >= 1.033 (CRQS bar) "
        "AND bootstrap CI lower bound > 0 "
        "AND MaxDD not worse than CRQS -22.5% bar "
        "AND End$1k >= CRQS $12,104 (ensemble must not sacrifice terminal value)"
    ),
    grid_size=5,
    primary_metric="sharpe",
)
print(f"Registered E44 as {reg.id}")

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

# ── Standalone baselines ──────────────────────────────────────────────────────
v2_sig = v2_signals(spy.reindex(panel.index), target_vol=0.18, lookback=20)
v2_ret = strategy_returns(spy.reindex(panel.index), v2_sig,
                          commission=COMMISSION, rf_daily=irx)

crqs_w = crqs_signals(spy.reindex(panel.index), shiller,
                      ief=ief.reindex(panel.index), gld=gld.reindex(panel.index),
                      eps_threshold=0.00, scale_down=0.75, corr_threshold=0.00,
                      target_vol=0.18, lookback=20)
crqs_ret = portfolio_returns(panel, crqs_w, commission=COMMISSION, rf_daily=irx)

mv_w = minvar_signals(panel, cov_lookback=60, sma_gate=False)
mv_ret = portfolio_returns(panel, mv_w, commission=COMMISSION, rf_daily=irx)

corr_crqs_mv = float(pd.Series(crqs_ret.values[:len(mv_ret)]).corr(
    pd.Series(mv_ret.values[:len(crqs_ret)])))
print(f"\nCRQS-MinVar return correlation: {corr_crqs_mv:.4f}")

# ── Grid search ──────────────────────────────────────────────────────────────
results = []
all_mean_sharpes = []

print("\n" + "=" * 70)
print("E44 CRQS + MINVAR ENSEMBLE GRID SEARCH")
print("=" * 70)

for bw in BLEND_GRID:
    label = f"CRQS+MV(w={bw:.2f})"

    w = ensemble_signals(panel, shiller,
                         ief=ief.reindex(panel.index),
                         gld=gld.reindex(panel.index),
                         blend_w=bw)
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
    corr_crqs = float(pd.Series(ret.values[:len(crqs_ret)]).corr(
        pd.Series(crqs_ret.values[:len(ret)])))

    results.append({
        "label": label,
        "blend_w": bw,
        "fold_sharpes": fold_sharpes,
        "mean_wf_oos": mean_wf,
        "max_dd_pct": min(fold_dds) * 100,
        "full_sample": m,
        "corr_v2": corr_v2,
        "corr_crqs": corr_crqs,
        "ret": ret,
    })

    print(f"\n{label}")
    print(f"  Folds: {[round(s,3) for s in fold_sharpes]}")
    print(f"  Mean WF OOS: {mean_wf:.3f}  MaxDD: {min(fold_dds)*100:.2f}%  "
          f"End$1k: {m['End$per1k']:.0f}")
    print(f"  Corr_v2: {corr_v2:.3f}  Corr_CRQS: {corr_crqs:.3f}")

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

# Comparison table
crqs_m = mmx(panel, crqs_w, commission=COMMISSION, rf_daily=irx, label="CRQS champion")
mv_m = mmx(panel, mv_w, commission=COMMISSION, rf_daily=irx, label="MinVar standalone")
spy_m = vmx(spy.reindex(panel.index),
            pd.Series(1.0, index=panel.index),
            commission=0.0, rf_daily=None, label="buy_hold_SPY")

print(f"\n{'Strategy':<30} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 62)
for row in [crqs_m, mv_m, best["full_sample"], spy_m]:
    print(f"{row['label']:<30} {row['Sharpe']:>7.3f} {row['MaxDD']:>8.2f}% "
          f"{row['End$per1k']:>8.0f} {row['CAGR']:>6.2f}%")

# ── Verdict ───────────────────────────────────────────────────────────────────
passes = (
    best["mean_wf_oos"] >= CRQS_MEAN_WF_BAR
    and ci.clears_noise
    and best["max_dd_pct"] > -22.5
    and dsr >= 0.95
    and best["full_sample"]["End$per1k"] >= 12104
)
verdict = "adopted" if passes else "discarded"

evidence = {
    "session": "s29_2026-08-04",
    "experiment": "E44_crqs_minvar_ensemble",
    "best_config": best["label"],
    "blend_w_best": best["blend_w"],
    "crqs_minvar_corr": round(corr_crqs_mv, 4),
    "mean_wf_oos": round(best["mean_wf_oos"], 4),
    "max_dd_pct": round(best["max_dd_pct"], 2),
    "dsr": round(dsr, 4),
    "ci_lo": round(ci.lo, 4),
    "ci_hi": round(ci.hi, 4),
    "ci_clears_zero": ci.clears_noise,
    "all_configs": [
        {"label": r["label"], "blend_w": r["blend_w"],
         "mean_wf_oos": round(r["mean_wf_oos"], 4),
         "max_dd_pct": round(r["max_dd_pct"], 2),
         "end1k": round(r["full_sample"]["End$per1k"], 0)}
        for r in results
    ],
}

print(f"\nVERDICT: {'PASSES' if passes else 'FAILS'} → {verdict.upper()}")
record_outcome(reg.id, verdict=verdict, evidence=evidence,
               notes=f"Session 29. {verdict.upper()}.")
print("\nE44 complete.")
