"""E46: CRQS + Trend Quality Filter (Variance Ratio) — session 31 (2026-08-07).

Hypothesis: Adding a variance-ratio-based Trend Quality Filter (TQF) to the CRQS
champion reduces equity exposure in choppy, low-autocorrelation markets where the
SMA200 generates whipsaw signals. This should improve risk-adjusted returns and
reduce drawdown without sacrificing trending-market gains.

Benchmark comparison: SPY buy-hold, DIA buy-hold, QQQ buy-hold, Mag-7 EW.
"""
import sys
import json
import itertools
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import load_ohlcv, load_shiller, load_vix, data_freshness
from backtest.multi_engine import portfolio_returns, metrics as mmx
from backtest.vector_engine import strategy_returns, metrics as vmx
from strategies.crqs import multi_signals as crqs_signals
from strategies.crqs_tqf import multi_signals as tqf_signals
from tools.trend_quality import trend_quality_summary
from backtest.evaluation import (
    deflated_sharpe_ratio, bootstrap_difference_ci, sharpe_ratio,
)
from research.preregister import preregister, record_outcome, trials_this_period

COMMISSION = 0.0015
FOLDS = [
    ("fold1_IS",  "2000-01-01", "2009-12-31"),
    ("fold2_OOS", "2010-01-01", "2019-12-31"),
    ("fold3_OOS", "2020-01-01", "2026-08-06"),
]
# Champion bars (from E42/E43 results, updated s30)
CRQS_MEAN_WF_BAR = 1.033   # CRQS champion OOS mean fold Sharpe
CRQS_END1K = 12104.0       # CRQS champion End$per1k (full-sample)

# ── Pre-registration ─────────────────────────────────────────────────────────
reg = preregister(
    hypothesis=(
        "E46 CRQS-TQF: Extending CRQS(eps=0.00, sd=0.75, ct=0.00) with a "
        "Variance Ratio Trend Quality Filter will reduce equity exposure in "
        "choppy/mean-reverting markets (VR ≤ 1.0), cutting whipsaw losses "
        "from the SMA200 signal while preserving trending-market returns. "
        "Parameters: vr_q ∈ {10,20,40} × vr_lb ∈ {63,126} × "
        "tqf_scale ∈ {0.50,0.75}. 12 configs. "
        "Research basis: Lo & MacKinlay (1988) variance ratio test; "
        "Chan (2013) trend quality; Moskowitz et al. (2012) time-series "
        "momentum works best in persistent regimes."
    ),
    success_criteria=(
        "Best config: Mean WF OOS Sharpe >= 1.033 (CRQS bar) "
        "AND bootstrap CI vs SPY lower bound > 0 "
        "AND MaxDD not worse than -22.5% "
        "AND DSR >= 0.95 "
        "AND End$per1k >= CRQS $12,104 (champion full-sample terminal value)."
    ),
    grid_size=12,
    primary_metric="sharpe",
)
print(f"Registered E46 as {reg.id}")

# ── Data ─────────────────────────────────────────────────────────────────────
freshness = data_freshness()
print(f"\nData freshness: {freshness}")

spy   = load_ohlcv("SPY",  "2000-01-01")["Close"]
ief   = load_ohlcv("IEF",  "2000-01-01")["Close"]
gld   = load_ohlcv("GLD",  "2000-01-01")["Close"]
irx   = load_ohlcv("^IRX", "2000-01-01")["Close"] / 100 / 252
shiller = load_shiller("2000-01-01")

panel = pd.DataFrame({"SPY": spy, "IEF": ief, "GLD": gld}).dropna(how="all")
panel = panel.ffill(limit=3)
irx  = irx.reindex(panel.index, method="ffill").fillna(0.0)
spy_aligned = spy.reindex(panel.index)
ief_aligned = ief.reindex(panel.index, method="ffill")
gld_aligned = gld.reindex(panel.index, method="ffill")
spy_ret_series = spy_aligned.pct_change().fillna(0.0)

# ── Current Trend Quality Summary ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("CURRENT TREND QUALITY STATUS")
print("=" * 70)
for q, w in [(10, 63), (20, 63), (40, 63), (20, 126)]:
    tq = trend_quality_summary(spy_ret_series, vr_q=q, vr_window=w)
    print(f"  VR(q={q:2d}, window={w:3d}): {tq['vr_current']:.4f} → "
          f"{tq['vr_regime']} | "
          f"trending% full={tq['vr_pct_trending_full']:.1%} "
          f"1yr={tq['vr_pct_trending_1yr']:.1%}")

# ── Benchmarks ────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("BENCHMARK PROFILES (full-sample, 2000-01-01 to 2026-08-06)")
print("=" * 70)

spy_sig_bh = pd.Series(1.0, index=panel.index)
spy_bh_m = vmx(spy_aligned, spy_sig_bh, commission=0.0, rf_daily=None,
               label="BuyHold_SPY")

dia = load_ohlcv("DIA", "2000-01-01")["Close"].reindex(panel.index, method="ffill")
dia_sig_bh = pd.Series(1.0, index=panel.index)
dia_bh_m = vmx(dia, dia_sig_bh, commission=0.0, rf_daily=None, label="BuyHold_DIA")

qqq = load_ohlcv("QQQ", "2000-01-01")["Close"].reindex(panel.index, method="ffill")
qqq_sig_bh = pd.Series(1.0, index=panel.index)
qqq_bh_m = vmx(qqq, qqq_sig_bh, commission=0.0, rf_daily=None, label="BuyHold_QQQ")

MAG7 = ["AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA"]
mag7_prices = {}
for t in MAG7:
    try:
        mag7_prices[t] = load_ohlcv(t, "2000-01-01")["Close"]
    except FileNotFoundError:
        print(f"  Mag-7: {t} not in cache, skipping")
mag7_panel = pd.DataFrame(mag7_prices).reindex(panel.index, method="ffill")
mag7_panel = mag7_panel.dropna(how="all")
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
    ief=ief_aligned,
    gld=gld_aligned,
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
    print(f"  {fname}: Sharpe={sr:.3f}")
print(f"  Mean WF OOS Sharpe: {np.mean(fold_sharpes_crqs[1:]):.3f}")
print(f"  MaxDD: {crqs_m['MaxDD']:.2f}%  End$1k: {crqs_m['End$per1k']:.0f}  "
      f"Sharpe: {crqs_m['Sharpe']:.3f}  CAGR: {crqs_m['CAGR']:.2f}%")

# ── E46: CRQS-TQF Grid Search ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("E46 CRQS-TQF GRID SEARCH (12 configs)")
print("=" * 70)

VR_Q   = [10, 20, 40]
VR_LB  = [63, 126]
TQF_SC = [0.50, 0.75]
CONFIGS = list(itertools.product(VR_Q, VR_LB, TQF_SC))
assert len(CONFIGS) == 12

results = []
all_mean_sharpes = []

for vr_q, vr_lb, tqf_scale in CONFIGS:
    label = f"TQF(q={vr_q:2d},lb={vr_lb:3d},sc={tqf_scale:.2f})"

    w = tqf_signals(
        spy_aligned, shiller,
        ief=ief_aligned,
        gld=gld_aligned,
        vr_q=vr_q, vr_lb=vr_lb, tqf_scale=tqf_scale,
        eps_threshold=0.00, scale_down=0.75,
        corr_threshold=0.00, corr_lb=63,
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

    # TQF activity: how often does TQF reduce equity vs CRQS?
    spy_diff = (crqs_w["SPY"].reindex(w.index) - w["SPY"]).clip(0, None)
    oos_mask = (w.index >= "2010-01-01")
    tqf_active_pct = float((spy_diff[oos_mask] > 0.01).mean()) * 100
    tqf_avg_reduction = float(spy_diff[oos_mask].mean()) * 100

    results.append({
        "label": label,
        "vr_q": vr_q, "vr_lb": vr_lb, "tqf_scale": tqf_scale,
        "fold_sharpes": fold_sharpes,
        "mean_wf_oos": mean_wf,
        "max_dd_pct": min(fold_dds) * 100,
        "full_sample": m,
        "tqf_active_pct": tqf_active_pct,
        "tqf_avg_reduction": tqf_avg_reduction,
        "ret": ret,
        "weights": w,
    })

    print(f"\n{label}")
    print(f"  Folds: {[round(s,3) for s in fold_sharpes]}")
    print(f"  Mean WF OOS: {mean_wf:.3f}  MaxDD: {min(fold_dds)*100:.2f}%  "
          f"End$1k: {m['End$per1k']:.0f}  Sharpe: {m['Sharpe']:.3f}  CAGR: {m['CAGR']:.2f}%")
    print(f"  TQF active (OOS): {tqf_active_pct:.1f}% of days, "
          f"avg equity reduction: {tqf_avg_reduction:.2f}%")

# ── Best Config Evaluation ────────────────────────────────────────────────────
best = max(results, key=lambda r: r["mean_wf_oos"])
best_ret = best["ret"]
n_trials = trials_this_period()

# DSR uses all 12 configs' mean WF OOS Sharpes
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
print(f"TQF active OOS: {best['tqf_active_pct']:.1f}% of days")
print(f"TQF avg equity reduction OOS: {best['tqf_avg_reduction']:.2f}%")

# ── Full Comparison Table ─────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("FULL COMPARISON: E46 vs Champion vs Benchmarks (full-sample)")
print(f"{'='*70}")
print(f"{'Strategy':<38} {'Sharpe':>7} {'MaxDD':>8} {'End$1k':>8} {'CAGR':>6}")
print("-" * 70)
for row in [crqs_m, best["full_sample"]]:
    print(f"{row['label']:<38} {row['Sharpe']:>7.3f} {row['MaxDD']:>8.2f}% "
          f"{row['End$per1k']:>8.0f} {row['CAGR']:>6.2f}%")
for bm in [spy_bh_m, dia_bh_m, qqq_bh_m, mag7_m]:
    print(f"{bm['label']:<38} {bm['Sharpe']:>7.3f} {bm['MaxDD']:>8.2f}% "
          f"{bm['End$per1k']:>8.0f} {bm['CAGR']:>6.2f}%")

# ── All Configs Ranking ───────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("ALL 12 CONFIGS RANKED BY MEAN WF OOS SHARPE")
print(f"{'='*70}")
sorted_results = sorted(results, key=lambda r: r["mean_wf_oos"], reverse=True)
print(f"{'Config':<35} {'MeanWF':>7} {'MaxDD':>8} {'End$1k':>8} {'TQF%':>6}")
print("-" * 65)
for r in sorted_results:
    marker = " ← BEST" if r["label"] == best["label"] else ""
    print(f"{r['label']:<35} {r['mean_wf_oos']:>7.3f} "
          f"{r['max_dd_pct']:>8.2f}% "
          f"{r['full_sample']['End$per1k']:>8.0f} "
          f"{r['tqf_active_pct']:>6.1f}%{marker}")

# ── Verdict ───────────────────────────────────────────────────────────────────
passes = (
    best["mean_wf_oos"] >= CRQS_MEAN_WF_BAR
    and ci.clears_noise
    and best["max_dd_pct"] > -22.5
    and dsr >= 0.95
    and best["full_sample"]["End$per1k"] >= CRQS_END1K
)
verdict = "adopted" if passes else "discarded"

# ── Current Signal ────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("CURRENT SIGNAL (2026-08-06)")
print(f"{'='*70}")

if passes:
    latest_w = best["weights"].iloc[-1]
    print(f"  BEST CONFIG WEIGHTS: SPY={latest_w['SPY']:.4f}  "
          f"IEF={latest_w['IEF']:.4f}  GLD={latest_w['GLD']:.4f}")
else:
    latest_w_crqs = crqs_w.iloc[-1]
    print(f"  CRQS CHAMPION (unchanged): SPY={latest_w_crqs['SPY']:.4f}  "
          f"IEF={latest_w_crqs['IEF']:.4f}  GLD={latest_w_crqs['GLD']:.4f}")

evidence = {
    "session": "s31_2026-08-07",
    "experiment": "E46_crqs_tqf",
    "best_config": best["label"],
    "best_vr_q": best["vr_q"],
    "best_vr_lb": best["vr_lb"],
    "best_tqf_scale": best["tqf_scale"],
    "mean_wf_oos": round(best["mean_wf_oos"], 4),
    "max_dd_pct": round(best["max_dd_pct"], 2),
    "dsr": round(dsr, 4),
    "ci_lo": round(ci.lo, 4),
    "ci_hi": round(ci.hi, 4),
    "ci_clears_zero": ci.clears_noise,
    "end_1k": round(best["full_sample"]["End$per1k"], 2),
    "crqs_end_1k": round(crqs_m["End$per1k"], 2),
    "crqs_bar_end_1k": CRQS_END1K,
    "tqf_active_pct": round(best["tqf_active_pct"], 2),
    "tqf_avg_reduction": round(best["tqf_avg_reduction"], 2),
    "n_trials_total": n_trials,
    "benchmarks": {
        "spy_bh": {"sharpe": spy_bh_m["Sharpe"], "end_1k": spy_bh_m["End$per1k"],
                   "maxdd": spy_bh_m["MaxDD"], "cagr": spy_bh_m["CAGR"]},
        "dia_bh": {"sharpe": dia_bh_m["Sharpe"], "end_1k": dia_bh_m["End$per1k"],
                   "maxdd": dia_bh_m["MaxDD"], "cagr": dia_bh_m["CAGR"]},
        "qqq_bh": {"sharpe": qqq_bh_m["Sharpe"], "end_1k": qqq_bh_m["End$per1k"],
                   "maxdd": qqq_bh_m["MaxDD"], "cagr": qqq_bh_m["CAGR"]},
        "mag7_ew": {"sharpe": mag7_m["Sharpe"], "end_1k": mag7_m["End$per1k"],
                    "maxdd": mag7_m["MaxDD"], "cagr": mag7_m["CAGR"]},
    },
    "crqs_champion": {
        "sharpe": crqs_m["Sharpe"],
        "end_1k": crqs_m["End$per1k"],
        "maxdd": crqs_m["MaxDD"],
        "cagr": crqs_m["CAGR"],
        "mean_wf_oos": round(np.mean(fold_sharpes_crqs[1:]), 4),
    },
    "all_configs": [
        {
            "label": r["label"],
            "vr_q": r["vr_q"],
            "vr_lb": r["vr_lb"],
            "tqf_scale": r["tqf_scale"],
            "mean_wf_oos": round(r["mean_wf_oos"], 4),
            "max_dd_pct": round(r["max_dd_pct"], 2),
            "end_1k": round(r["full_sample"]["End$per1k"], 2),
            "tqf_active_pct": round(r["tqf_active_pct"], 2),
        }
        for r in results
    ],
}

print(f"\nVERDICT: {'PASSES' if passes else 'FAILS'} → {verdict.upper()}")
record_outcome(reg.id, verdict=verdict, evidence=evidence,
               notes=f"Session 31. {verdict.upper()}. Variance Ratio Trend Quality Filter.")
print("\nE46 complete.")

# Save evidence to JSON for the session report
out_path = Path(__file__).parent / f"results_s31_e46_tqf.json"
out_path.write_text(json.dumps(evidence, indent=2))
print(f"Evidence saved to {out_path}")
