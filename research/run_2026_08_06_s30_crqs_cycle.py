"""E45: CRQS-CycleOverlay — session 30 (2026-08-06).

Hypothesis: Extending the CRQS champion with a Howard Marks market-cycle
tilt — pre-emptively reducing equity when the cycle composite score
(CAPE valuation + VIX complacency + 12-month momentum + ERP) exceeds a
threshold AND the EPS quality gate is INACTIVE — improves risk-adjusted
returns versus the CRQS champion in the OOS period.

The cycle overlay fires ONLY when:
  (a) normalised_cycle_score > cycle_threshold, AND
  (b) EPS quality gate is INACTIVE (earnings not falling)
This prevents double-penalising in downturns (when CRQS already cuts equity).

Parameters (6 configs = 3 thresholds × 2 scale-factors):
  cycle_threshold ∈ {0.70, 0.75, 0.80}
  cycle_scale     ∈ {0.80, 0.90}

Benchmark comparison: SPY buy-hold, DIA buy-hold, QQQ buy-hold, Mag-7 EW.
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import itertools

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import load_ohlcv, load_shiller, load_vix, data_freshness
from backtest.multi_engine import portfolio_returns, metrics as mmx
from backtest.vector_engine import strategy_returns, metrics as vmx
from strategies.vol_target import signals as v2_signals
from strategies.crqs import multi_signals as crqs_signals
from strategies.crqs_cycle_overlay import multi_signals as cycle_signals
from backtest.evaluation import (
    deflated_sharpe_ratio, bootstrap_difference_ci, sharpe_ratio,
)
from research.preregister import preregister, record_outcome, trials_this_period

COMMISSION = 0.0015
FOLDS = [
    ("fold1_IS",  "2000-01-01", "2009-12-31"),
    ("fold2_OOS", "2010-01-01", "2019-12-31"),
    ("fold3_OOS", "2020-01-01", "2026-08-05"),
]
# Champion bars (from E42/E43 results)
CRQS_MEAN_WF_BAR = 1.033   # CRQS champion OOS mean fold Sharpe
CRQS_END1K = 12104.0       # CRQS champion End$per1k (full-sample)

# ── Pre-registration ─────────────────────────────────────────────────────────
reg = preregister(
    hypothesis=(
        "E45 CRQS-CycleOverlay: Extending CRQS(eps=0.00, sd=0.75, ct=0.00) with "
        "a Howard Marks 4-component market-cycle tilt (CAPE valuation 25%, VIX "
        "complacency 20%, 12m momentum 20%, ERP 15%; EPS quality excluded — CRQS "
        "handles it) will improve OOS risk-adjusted returns vs the CRQS champion. "
        "Tilt fires only when cycle_score > threshold AND EPS gate INACTIVE. "
        "Expected: modest improvement in Sharpe and/or MaxDD in late-bull environments; "
        "possible wash as overlay fires on only ~8-15% of OOS days. "
        "Parameters: cycle_threshold ∈ {0.70,0.75,0.80} × cycle_scale ∈ {0.80,0.90}. "
        "6 configs. Reference: Marks (2018) 'Mastering the Market Cycle'."
    ),
    success_criteria=(
        "Best config: Mean WF OOS Sharpe >= 1.033 (CRQS bar) "
        "AND bootstrap CI vs SPY lower bound > 0 "
        "AND MaxDD not worse than -22.5% "
        "AND DSR >= 0.95 "
        "AND End$per1k >= CRQS $12,104 (champion full-sample terminal value)."
    ),
    grid_size=6,
    primary_metric="sharpe",
)
print(f"Registered E45 as {reg.id}")

# ── Data ─────────────────────────────────────────────────────────────────────
freshness = data_freshness()
print(f"\nData freshness: {freshness}")

spy   = load_ohlcv("SPY",  "2000-01-01")["Close"]
ief   = load_ohlcv("IEF",  "2000-01-01")["Close"]
gld   = load_ohlcv("GLD",  "2000-01-01")["Close"]
irx   = load_ohlcv("^IRX", "2000-01-01")["Close"] / 100 / 252
vix_df = load_vix("2000-01-01")
vix   = vix_df["CLOSE"]                     # uppercase CLOSE column
shiller = load_shiller("2000-01-01")

panel = pd.DataFrame({"SPY": spy, "IEF": ief, "GLD": gld}).dropna(how="all")
panel = panel.ffill(limit=3)
irx  = irx.reindex(panel.index, method="ffill").fillna(0.0)
spy_aligned = spy.reindex(panel.index)
vix_aligned = vix.reindex(panel.index, method="ffill")
spy_ret_series = spy_aligned.pct_change().fillna(0.0)

# ── Benchmarks ────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("BENCHMARK PROFILES (full-sample, 2000-01-01 to 2026-08-05)")
print("=" * 70)

# Buy-hold SPY
spy_sig_bh = pd.Series(1.0, index=panel.index)
spy_bh_m = vmx(spy_aligned, spy_sig_bh, commission=0.0, rf_daily=None,
               label="BuyHold_SPY")

# Buy-hold DIA
dia = load_ohlcv("DIA", "2000-01-01")["Close"].reindex(panel.index, method="ffill")
dia_sig_bh = pd.Series(1.0, index=panel.index)
dia_bh_m = vmx(dia, dia_sig_bh, commission=0.0, rf_daily=None, label="BuyHold_DIA")

# Buy-hold QQQ
qqq = load_ohlcv("QQQ", "2000-01-01")["Close"].reindex(panel.index, method="ffill")
qqq_sig_bh = pd.Series(1.0, index=panel.index)
qqq_bh_m = vmx(qqq, qqq_sig_bh, commission=0.0, rf_daily=None, label="BuyHold_QQQ")

# Mag-7 Equal Weight (AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA)
MAG7 = ["AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA"]
mag7_prices = {}
for t in MAG7:
    try:
        mag7_prices[t] = load_ohlcv(t, "2000-01-01")["Close"]
    except FileNotFoundError:
        print(f"  Mag-7: {t} not in cache, skipping")
mag7_panel = pd.DataFrame(mag7_prices).reindex(panel.index, method="ffill")
mag7_panel = mag7_panel.dropna(how="all")
# EW monthly rebal: each ticker gets 1/N weight (wherever data available)
mag7_n = mag7_panel.notna().sum(axis=1).clip(lower=1)
mag7_ret = mag7_panel.pct_change().fillna(0.0)
mag7_ew_ret = (mag7_ret / mag7_n.shift(1).fillna(1.0)).sum(axis=1)
mag7_eq = (1 + mag7_ew_ret).cumprod()
mag7_years = (mag7_eq.index[-1] - mag7_eq.index[0]).days / 365.25
mag7_cagr = mag7_eq.iloc[-1] ** (1 / mag7_years) - 1
mag7_sharpe = mag7_ew_ret.mean() / mag7_ew_ret.std() * np.sqrt(252)
mag7_dd = (mag7_eq / mag7_eq.cummax() - 1).min()
mag7_m = {
    "label": "Mag7_EqualWeight",
    "CAGR": round(mag7_cagr * 100, 2),
    "Sharpe": round(float(mag7_sharpe), 3),
    "MaxDD": round(float(mag7_dd) * 100, 2),
    "End$per1k": round(1000 * float(mag7_eq.iloc[-1]), 2),
}

print(f"\n{'Strategy':<35} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 65)
for bm in [spy_bh_m, dia_bh_m, qqq_bh_m, mag7_m]:
    print(f"{bm['label']:<35} {bm['Sharpe']:>7.3f} {bm['MaxDD']:>8.2f}% "
          f"{bm['End$per1k']:>8.0f} {bm['CAGR']:>6.2f}%")

# ── CRQS Champion Baseline ────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CRQS CHAMPION BASELINE (eps=0.00, sd=0.75, ct=0.00)")
print("=" * 70)

crqs_w = crqs_signals(
    spy_aligned, shiller,
    ief=ief.reindex(panel.index, method="ffill"),
    gld=gld.reindex(panel.index, method="ffill"),
    eps_threshold=0.00, scale_down=0.75,
    corr_threshold=0.00, corr_lb=63,
    target_vol=0.18, lookback=20,
)
crqs_ret = portfolio_returns(panel, crqs_w, commission=COMMISSION, rf_daily=irx)
crqs_m   = mmx(panel, crqs_w, commission=COMMISSION, rf_daily=irx, label="CRQS_champion")

fold_sharpes_crqs = []
for fname, fs, fe in FOLDS:
    r_fold = crqs_ret.loc[fs:fe]
    sr = sharpe_ratio(r_fold.values)
    fold_sharpes_crqs.append(sr)
print(f"  Fold Sharpes: {[round(s,3) for s in fold_sharpes_crqs]}")
print(f"  Mean WF OOS Sharpe: {np.mean(fold_sharpes_crqs[1:]):.3f}")
print(f"  MaxDD: {crqs_m['MaxDD']:.2f}%  End$1k: {crqs_m['End$per1k']:.0f}  "
      f"Sharpe: {crqs_m['Sharpe']:.3f}")

# ── E45: CRQS-CycleOverlay Grid Search ───────────────────────────────────────
print("\n" + "=" * 70)
print("E45 CRQS-CYCLEOVERLAY GRID SEARCH")
print("=" * 70)

THRESHOLDS = [0.70, 0.75, 0.80]
SCALES     = [0.80, 0.90]
CONFIGS    = list(itertools.product(THRESHOLDS, SCALES))

results = []
all_mean_sharpes = []

for ct, cs in CONFIGS:
    label = f"CycleOverlay(th={ct:.2f},sc={cs:.2f})"

    w = cycle_signals(
        spy_aligned, shiller, vix_aligned,
        ief=ief.reindex(panel.index, method="ffill"),
        gld=gld.reindex(panel.index, method="ffill"),
        rf_daily=irx,
        eps_threshold=0.00, scale_down=0.75,
        corr_threshold=0.00, corr_lb=63,
        cycle_threshold=ct, cycle_scale=cs,
        vix_lb=252 * 5,
        target_vol=0.18, lookback=20,
    )
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

    # Measure how often the cycle tilt actually fires (in OOS)
    # cycle_active = 1 when both tilt fires and gate inactive
    # We can approximate by checking how much equity_sig differs from crqs_sig
    spy_diff = (w["SPY"] - crqs_w.reindex(w.index)["SPY"]).abs()
    oos_mask = (w.index >= "2010-01-01")
    tilt_active_pct = float((spy_diff[oos_mask] > 0.001).mean()) * 100

    results.append({
        "label": label,
        "cycle_threshold": ct,
        "cycle_scale": cs,
        "fold_sharpes": fold_sharpes,
        "mean_wf_oos": mean_wf,
        "max_dd_pct": min(fold_dds) * 100,
        "full_sample": m,
        "tilt_active_pct": tilt_active_pct,
        "ret": ret,
    })

    print(f"\n{label}")
    print(f"  Folds: {[round(s,3) for s in fold_sharpes]}")
    print(f"  Mean WF OOS: {mean_wf:.3f}  MaxDD: {min(fold_dds)*100:.2f}%  "
          f"End$1k: {m['End$per1k']:.0f}  Sharpe: {m['Sharpe']:.3f}")
    print(f"  Tilt active (OOS): {tilt_active_pct:.1f}% of days")

# ── Best Config Evaluation ────────────────────────────────────────────────────
best = max(results, key=lambda r: r["mean_wf_oos"])
best_ret = best["ret"]
n_trials = trials_this_period()
dsr = deflated_sharpe_ratio(best_ret.values,
                             [s / np.sqrt(252) for s in all_mean_sharpes])
ci  = bootstrap_difference_ci(best_ret.values, spy_ret_series.values,
                               metric="sharpe", n=10000, seed=0)

print(f"\n{'='*70}")
print(f"BEST CONFIG: {best['label']}")
print(f"Mean WF OOS Sharpe: {best['mean_wf_oos']:.4f}  (bar: {CRQS_MEAN_WF_BAR})")
print(f"MaxDD: {best['max_dd_pct']:.2f}%  (bar: -22.5%)")
print(f"End$1k: {best['full_sample']['End$per1k']:.0f}  (bar: {CRQS_END1K:.0f})")
print(f"DSR: {dsr:.4f}  (bar: 0.95)")
print(f"CI vs SPY: [{ci.lo:.4f}, {ci.hi:.4f}]  Clears zero: {ci.clears_noise}")
print(f"Tilt active OOS: {best['tilt_active_pct']:.1f}% of days")

# ── Full Comparison Table ─────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("FULL COMPARISON: E45 vs Champion vs Benchmarks (full-sample)")
print(f"{'='*70}")
print(f"{'Strategy':<38} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 70)
for row in [crqs_m, best["full_sample"]]:
    print(f"{row['label']:<38} {row['Sharpe']:>7.3f} {row['MaxDD']:>8.2f}% "
          f"{row['End$per1k']:>8.0f} {row['CAGR']:>6.2f}%")
for bm in [spy_bh_m, dia_bh_m, qqq_bh_m, mag7_m]:
    print(f"{bm['label']:<38} {bm['Sharpe']:>7.3f} {bm['MaxDD']:>8.2f}% "
          f"{bm['End$per1k']:>8.0f} {bm['CAGR']:>6.2f}%")

# ── Verdict ───────────────────────────────────────────────────────────────────
passes = (
    best["mean_wf_oos"] >= CRQS_MEAN_WF_BAR
    and ci.clears_noise
    and best["max_dd_pct"] > -22.5
    and dsr >= 0.95
    and best["full_sample"]["End$per1k"] >= CRQS_END1K
)
verdict = "adopted" if passes else "discarded"

evidence = {
    "session": "s30_2026-08-06",
    "experiment": "E45_crqs_cycle_overlay",
    "best_config": best["label"],
    "best_cycle_threshold": best["cycle_threshold"],
    "best_cycle_scale": best["cycle_scale"],
    "mean_wf_oos": round(best["mean_wf_oos"], 4),
    "max_dd_pct": round(best["max_dd_pct"], 2),
    "dsr": round(dsr, 4),
    "ci_lo": round(ci.lo, 4),
    "ci_hi": round(ci.hi, 4),
    "ci_clears_zero": ci.clears_noise,
    "end_1k": round(best["full_sample"]["End$per1k"], 2),
    "crqs_bar_end_1k": CRQS_END1K,
    "tilt_active_pct": round(best["tilt_active_pct"], 2),
    "n_trials_total": n_trials,
    "benchmarks": {
        "spy_bh": {"sharpe": spy_bh_m["Sharpe"], "end_1k": spy_bh_m["End$per1k"]},
        "dia_bh": {"sharpe": dia_bh_m["Sharpe"], "end_1k": dia_bh_m["End$per1k"]},
        "qqq_bh": {"sharpe": qqq_bh_m["Sharpe"], "end_1k": qqq_bh_m["End$per1k"]},
        "mag7_ew": {"sharpe": mag7_m["Sharpe"], "end_1k": mag7_m["End$per1k"]},
    },
    "all_configs": [
        {
            "label": r["label"],
            "cycle_threshold": r["cycle_threshold"],
            "cycle_scale": r["cycle_scale"],
            "mean_wf_oos": round(r["mean_wf_oos"], 4),
            "max_dd_pct": round(r["max_dd_pct"], 2),
            "tilt_active_pct": round(r["tilt_active_pct"], 2),
        }
        for r in results
    ],
}

print(f"\nVERDICT: {'PASSES' if passes else 'FAILS'} → {verdict.upper()}")
record_outcome(reg.id, verdict=verdict, evidence=evidence,
               notes=f"Session 30. {verdict.upper()}. Howard Marks cycle overlay.")
print("\nE45 complete.")
