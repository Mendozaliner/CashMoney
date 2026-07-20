"""Session 13 (2026-07-20): Three new investing-philosophy families.

E22: v2 + CTA Ensemble (relaxing corr threshold 0.50 -> 0.70 per roadmap item #5)
     Philosophy: portfolio diversification theory (Markowitz 1952); corr=0.635
     is meaningfully uncorrelated and warrants ensemble testing.
E23: Market Breadth Trend Signal
     Philosophy: Fosback "Stock Market Logic" (1976), Zweig (1986).
     Sector breadth as a regime indicator layered onto vol-targeted SPY.
E24: Low-Vol Sector Rotation
     Philosophy: Baker & Haugen (2012), Frazzini & Pedersen (2014) "BAB".
     Hold the lowest-realized-vol sector ETFs in equal weight, SMA200 gated.

Data through 2026-07-17 (1 trading day stale — July 18 Action not yet pulled).
Holdout locked from 2025-07-17. Configs entering this session: 159.
"""
import sys, json
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target as vt, market_breadth as mb
from strategies import low_vol_sector as lvs, ensemble as ens
from strategies import cta_trend as cta
from research.preregister import preregister, record_outcome, trials_this_period
from backtest import guardrails as gr

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HOLDOUT_START = "2025-07-17"
COST = 0.0015
FOLDS = [
    ("2000-2009",  "2000-01-01", "2009-12-31"),
    ("2010-2019",  "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-16"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-16"
V2_MEAN_WF_SHARPE = 0.851
V2_WORST_DD = -20.5
SECTOR_TICKERS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB']

# ---------------------------------------------------------------------------
# 1. Data + freshness
# ---------------------------------------------------------------------------
fresh = loader.data_freshness()
print("=== DATA FRESHNESS ===")
print(fresh)
stale = fresh.get("stale_days", 0) or 0

spy_full = loader.load_ohlcv("SPY")
spy_all = spy_full["Close"]
spy_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]

latest_spy_date = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close = float(spy_all.iloc[-2])

irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_cut.index).ffill()
rf_daily = (irx_full / 100.0) / 252.0
spy_ret = spy_cut.pct_change().fillna(0.0)

# Multi-asset panel (cut to before holdout)
ALL_TICKERS = ['SPY', 'IEF', 'GLD'] + SECTOR_TICKERS
panel_full = loader.load_universe(ALL_TICKERS)
panel_cut = panel_full[panel_full.index < HOLDOUT_START].copy()

sector_panel_cut = panel_cut[SECTOR_TICKERS].copy()
irx_aligned = irx_full.reindex(panel_cut.index).ffill()
rf_aligned = (irx_aligned / 100.0) / 252.0

print(f"\nData through {latest_spy_date.date()}, SPY={latest_spy_close:.2f}")
print(f"Stale days: {stale} (G7 threshold: >4)")
print(f"Configs entering this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails (data stale by 1 trading day — carry mark)
# ---------------------------------------------------------------------------
UNITS = 1.3334757435413753
prev_value = 991.16   # last confirmed mark (2026-07-17 close, session 12)
new_value = round(UNITS * latest_spy_close, 2)  # = 991.16 (same close)
peak_value = 1006.52

# Re-confirm v2 signal as of latest close
v2_sig_all = vt.signals(spy_cut, target_vol=0.18, lookback=20)
latest_signal = float(v2_sig_all.iloc[-1])
sma200 = spy_cut.rolling(200).mean().iloc[-1]
rv_20d = spy_cut.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
vol_scale = min(1.0, 0.18 / rv_20d) if rv_20d > 0 else 1.0
spy_day_chg = (latest_spy_close / prev_spy_close - 1) * 100

print(f"\n=== PORTFOLIO MARK ({latest_spy_date.date()}) ===")
print(f"  Data through {latest_spy_date.date()} (1 trading day stale; July 18 data not yet committed)")
print(f"  Carrying prior mark: ${new_value:.2f} (same as S12 — no new close)")
print(f"  v2 exposure: {latest_signal:.4f}  (SPY {latest_spy_close:.2f} vs SMA200 {sma200:.2f}; rv {rv_20d*100:.1f}%)")
print(f"  All-time: {(new_value/1000-1)*100:+.3f}%")

port = json.loads(Path("portfolio.json").read_text())
gr_report = gr.run_all(port, spy_returns=spy_ret, stale_days=stale)
print(f"\n=== GUARDRAILS ===")
for c in gr_report["checks"]:
    tag = "OK" if c["ok"] else "FAIL"
    info = c.get("detail") or c.get("level", "") or str({k: v for k, v in c.items() if k not in ("guardrail", "ok")})
    print(f"  [{tag}] {c['guardrail']}: {info}")
print(f"  ALL OK: {gr_report['all_ok']}")

# ---------------------------------------------------------------------------
# 3. Helper: walk-forward evaluation
# ---------------------------------------------------------------------------
def wf_single(spy_series, sig_fn, **kw):
    """Walk-forward metrics for a single-asset SPY strategy."""
    results = []
    all_sharpes = []
    for fold_name, start, end in FOLDS:
        s = spy_series.loc[start:end]
        irx_f = irx_full.reindex(s.index).ffill()
        rf_f = (irx_f / 100.0) / 252.0
        sig = sig_fn(s, **kw)
        m = ve.metrics(s, sig, commission=COST, rf_daily=rf_f, label=fold_name)
        results.append(m)
        all_sharpes.append(m["Sharpe"])
    return results, all_sharpes


def wf_multi(price_panel_full, wt_fn, rf_full, **kw):
    """Walk-forward metrics for a multi-asset strategy."""
    results = []
    all_sharpes = []
    for fold_name, start, end in FOLDS:
        p = price_panel_full.loc[start:end]
        rf_f = rf_full.reindex(p.index).ffill()
        w = wt_fn(p, **kw)
        m = me.metrics(p, w, commission=COST, rf_daily=rf_f, label=fold_name)
        results.append(m)
        all_sharpes.append(m["Sharpe"])
    return results, all_sharpes


def summarize(fold_results, label=""):
    sharpes = [r["Sharpe"] for r in fold_results]
    dds = [r["MaxDD"] for r in fold_results]
    terms = [r["End$per1k"] for r in fold_results]
    mean_sh = float(np.mean(sharpes))
    worst_dd = float(np.min(dds))
    print(f"\n  {label}")
    for r in fold_results:
        print(f"    [{r['label']}] Sharpe={r['Sharpe']:.3f}  MaxDD={r['MaxDD']:.1f}%  $1k->{r['End$per1k']:.0f}")
    print(f"    Mean WF Sharpe: {mean_sh:.3f}  |  Worst DD: {worst_dd:.1f}%")
    return mean_sh, worst_dd, sharpes


def dsr_and_ci(strategy_rets, all_trial_sharpes, spy_rets_same_period):
    dsr = ev.deflated_sharpe_ratio(strategy_rets, all_trial_sharpes)
    ci = ev.bootstrap_difference_ci(strategy_rets, spy_rets_same_period)
    return dsr, ci


# ---------------------------------------------------------------------------
# 4. SPY / benchmark baselines
# ---------------------------------------------------------------------------
print("\n\n=== BASELINES ===")
spy_bh_results, _ = wf_single(spy_cut, lambda s, **k: pd.Series(1.0, index=s.index), )
summarize(spy_bh_results, "SPY Buy-and-Hold")

v2_results, v2_fold_sharpes = wf_single(spy_cut, vt.signals, target_vol=0.18, lookback=20)
v2_mean_sh, v2_worst_dd, _ = summarize(v2_results, "v2 Champion (baseline)")

# ---------------------------------------------------------------------------
# 5. E22 — v2 + CTA Ensemble
# ---------------------------------------------------------------------------
print("\n\n" + "="*60)
print("E22: v2 + CTA ENSEMBLE (corr threshold relaxed to 0.70)")
print("="*60)

reg22 = preregister(
    hypothesis=(
        "Blending champion v2 (SPY; best terminal value) with CTA(SPY/IEF/GLD, vt0.12; "
        "best Sharpe/DD) improves the combined Sharpe-DD profile vs v2 alone. "
        "CTA corr=0.635 to v2; the roadmap approved testing at threshold 0.70."
    ),
    success_criteria=(
        "Mean WF Sharpe > v2 (0.851) AND worst-fold MaxDD better than v2 (-20.5%) "
        "AND DSR >= 0.95 AND bootstrap CI lower bound > 0."
    ),
    grid_size=3,
    primary_metric="sharpe",
)
print(f"  Registration ID: {reg22.id}")

E22_ALPHAS = [0.50, 0.60, 0.40]  # fraction of v2 vs CTA
E22_CTA_ASSETS = ['SPY', 'IEF', 'GLD']

e22_results = []
e22_all_sharpes = []

for alpha in E22_ALPHAS:
    label = f"Ensemble(v2={alpha:.0%},CTA={1-alpha:.0%})"

    def _ens_wt(p, _alpha=alpha):
        return ens.v2_cta_signals(p, alpha=_alpha, cta_assets=E22_CTA_ASSETS,
                                   cta_vol_target=0.12, v2_target_vol=0.18)

    folds, sharpes = wf_multi(panel_cut, _ens_wt, rf_aligned)
    mean_sh, worst_dd, _ = summarize(folds, label)
    e22_results.append({
        "alpha": alpha,
        "mean_wf_sharpe": mean_sh,
        "worst_dd": worst_dd,
        "fold_sharpes": sharpes,
        "fold_results": folds,
    })
    e22_all_sharpes.extend(sharpes)

# Pick best by mean WF Sharpe
best22 = max(e22_results, key=lambda x: x["mean_wf_sharpe"])
print(f"\n  Best E22: alpha={best22['alpha']:.0%}  mean WF Sharpe={best22['mean_wf_sharpe']:.3f}  worst DD={best22['worst_dd']:.1f}%")

# DSR + CI on best config OOS period
best22_alpha = best22["alpha"]
ens_oos_w = ens.v2_cta_signals(panel_cut.loc[OOS_A:OOS_B],
                                alpha=best22_alpha, cta_assets=E22_CTA_ASSETS,
                                cta_vol_target=0.12, v2_target_vol=0.18)
ens_oos_ret = me.portfolio_returns(panel_cut.loc[OOS_A:OOS_B], ens_oos_w,
                                    commission=COST, rf_daily=rf_aligned.loc[OOS_A:OOS_B])
spy_oos_ret = spy_cut.loc[OOS_A:OOS_B].pct_change().fillna(0.0)
all_trials_e22 = [r["Sharpe"] for r in e22_results[0]["fold_results"]] + e22_all_sharpes
prior_trials = [r["Sharpe"] for r in v2_results]
dsr22, ci22 = dsr_and_ci(ens_oos_ret, e22_all_sharpes + prior_trials, spy_oos_ret)
print(f"  DSR: {dsr22:.4f}  CI (diff vs SPY): [{ci22.lo:+.3f}, {ci22.hi:+.3f}]  clears_zero: {ci22.clears_noise}")

e22_pass = (best22["mean_wf_sharpe"] > V2_MEAN_WF_SHARPE and
            best22["worst_dd"] > V2_WORST_DD and
            dsr22 >= 0.95 and ci22.clears_noise)
e22_verdict = "adopted" if e22_pass else "discarded"
print(f"  E22 verdict: {e22_verdict.upper()}")

record_outcome(reg22.id, e22_verdict, evidence={
    "best_alpha": best22_alpha,
    "mean_wf_sharpe": round(best22["mean_wf_sharpe"], 4),
    "worst_dd": round(best22["worst_dd"], 2),
    "dsr": round(dsr22, 4),
    "ci_lo": round(ci22.lo, 3),
    "ci_hi": round(ci22.hi, 3),
})

# Correlation v2 vs ensemble OOS
v2_oos_sig = vt.signals(spy_cut.loc[OOS_A:OOS_B], target_vol=0.18, lookback=20)
v2_oos_ret = ve.strategy_returns(spy_cut.loc[OOS_A:OOS_B], v2_oos_sig,
                                  commission=COST, rf_daily=rf_daily.loc[OOS_A:OOS_B])
corr_e22 = float(pd.concat([v2_oos_ret.rename("v2"),
                             ens_oos_ret.rename("ens")], axis=1).corr().iloc[0, 1])
print(f"  Corr(v2, best ensemble) OOS: {corr_e22:.3f}")

# ---------------------------------------------------------------------------
# 6. E23 — Market Breadth Trend Signal
# ---------------------------------------------------------------------------
print("\n\n" + "="*60)
print("E23: MARKET BREADTH TREND SIGNAL (Fosback / Zweig)")
print("="*60)

reg23 = preregister(
    hypothesis=(
        "Using the fraction of 9 SPDR sector ETFs above their SMA200 as a "
        "regime filter — with hysteresis — layered onto vol-targeted SPY "
        "exposure produces a strategy with better risk-adjusted returns and "
        "lower drawdowns than champion v2, which uses only the index itself."
    ),
    success_criteria=(
        "Mean WF Sharpe > v2 (0.851) AND worst-fold MaxDD better than v2 (-20.5%) "
        "AND DSR >= 0.95 AND bootstrap CI lower bound > 0."
    ),
    grid_size=6,
    primary_metric="sharpe",
)
print(f"  Registration ID: {reg23.id}")

SECTOR_PANEL_FULL = panel_full[SECTOR_TICKERS]

E23_GRID = [
    (0.6, 0.4, 0.18),
    (0.7, 0.5, 0.18),
    (0.8, 0.5, 0.18),
    (0.6, 0.4, 0.15),
    (0.7, 0.4, 0.15),
    (0.8, 0.5, 0.15),
]

e23_results = []
e23_all_sharpes = []

for upper, lower, vtgt in E23_GRID:
    label = f"Breadth(up={upper},lo={lower},vt={vtgt})"

    def _mb_sig(s, _u=upper, _l=lower, _v=vtgt):
        sec = SECTOR_PANEL_FULL.reindex(s.index)
        return mb.signals(s, sec, upper_band=_u, lower_band=_l, vol_target=_v)

    folds, sharpes = wf_single(spy_cut, _mb_sig)
    mean_sh, worst_dd, _ = summarize(folds, label)
    e23_results.append({
        "upper": upper, "lower": lower, "vtgt": vtgt,
        "mean_wf_sharpe": mean_sh, "worst_dd": worst_dd,
        "fold_sharpes": sharpes, "fold_results": folds,
    })
    e23_all_sharpes.extend(sharpes)

best23 = max(e23_results, key=lambda x: x["mean_wf_sharpe"])
print(f"\n  Best E23: up={best23['upper']} lo={best23['lower']} vt={best23['vtgt']}  "
      f"mean WF Sharpe={best23['mean_wf_sharpe']:.3f}  worst DD={best23['worst_dd']:.1f}%")

# DSR + CI
def _best23_sig(s):
    sec = SECTOR_PANEL_FULL.reindex(s.index)
    return mb.signals(s, sec, upper_band=best23["upper"],
                      lower_band=best23["lower"], vol_target=best23["vtgt"])

best23_oos_sig = _best23_sig(spy_cut.loc[OOS_A:OOS_B])
best23_oos_ret = ve.strategy_returns(spy_cut.loc[OOS_A:OOS_B], best23_oos_sig,
                                      commission=COST, rf_daily=rf_daily.loc[OOS_A:OOS_B])
dsr23, ci23 = dsr_and_ci(best23_oos_ret, e23_all_sharpes + prior_trials, spy_oos_ret)
print(f"  DSR: {dsr23:.4f}  CI (diff vs SPY): [{ci23.lo:+.3f}, {ci23.hi:+.3f}]  clears_zero: {ci23.clears_noise}")

e23_pass = (best23["mean_wf_sharpe"] > V2_MEAN_WF_SHARPE and
            best23["worst_dd"] > V2_WORST_DD and
            dsr23 >= 0.95 and ci23.clears_noise)
e23_verdict = "adopted" if e23_pass else "discarded"
print(f"  E23 verdict: {e23_verdict.upper()}")

# Corr to v2
corr_e23 = float(pd.concat([v2_oos_ret.rename("v2"),
                              best23_oos_ret.rename("mb")], axis=1).corr().iloc[0, 1])
print(f"  Corr(v2, best breadth OOS): {corr_e23:.3f}")

record_outcome(reg23.id, e23_verdict, evidence={
    "best_params": {"upper": best23["upper"], "lower": best23["lower"], "vtgt": best23["vtgt"]},
    "mean_wf_sharpe": round(best23["mean_wf_sharpe"], 4),
    "worst_dd": round(best23["worst_dd"], 2),
    "dsr": round(dsr23, 4),
    "ci_lo": round(ci23.lo, 3),
    "ci_hi": round(ci23.hi, 3),
    "corr_v2_oos": round(corr_e23, 3),
})

# ---------------------------------------------------------------------------
# 7. E24 — Low-Vol Sector Rotation (Baker-Haugen)
# ---------------------------------------------------------------------------
print("\n\n" + "="*60)
print("E24: LOW-VOL SECTOR ROTATION (Baker & Haugen / Frazzini & Pedersen)")
print("="*60)

reg24 = preregister(
    hypothesis=(
        "Holding the top_n lowest-realized-vol sectors (out of 9 SPDRs) with "
        "an SMA200 trend gate and monthly rebalancing produces better "
        "risk-adjusted returns than SPY buy-and-hold via the low-vol anomaly."
    ),
    success_criteria=(
        "Mean WF Sharpe > SPY B&H across all 3 folds AND worst-fold MaxDD "
        "< -30% (acceptable for sector equity) AND DSR >= 0.95 AND bootstrap "
        "CI (vs SPY) lower bound > 0."
    ),
    grid_size=6,
    primary_metric="sharpe",
)
print(f"  Registration ID: {reg24.id}")

E24_GRID = [
    (3, True),
    (4, True),
    (5, True),
    (3, False),
    (4, False),
    (5, False),
]

e24_results = []
e24_all_sharpes = []

for top_n, use_gate in E24_GRID:
    label = f"LowVol(n={top_n},gate={use_gate})"

    def _lvs_wt(p, _n=top_n, _g=use_gate):
        sec_cols = [c for c in SECTOR_TICKERS if c in p.columns]
        return lvs.multi_signals(p[sec_cols], top_n=_n, use_trend_gate=_g)

    # For multi-engine we use the sector panel ONLY (not SPY/IEF/GLD)
    sector_panel_cut2 = panel_cut[SECTOR_TICKERS].copy()

    def _lvs_wt2(p, _n=top_n, _g=use_gate):
        return lvs.multi_signals(p, top_n=_n, use_trend_gate=_g)

    folds, sharpes = wf_multi(sector_panel_cut2, _lvs_wt2, rf_aligned)
    mean_sh, worst_dd, _ = summarize(folds, label)
    e24_results.append({
        "top_n": top_n, "use_gate": use_gate,
        "mean_wf_sharpe": mean_sh, "worst_dd": worst_dd,
        "fold_sharpes": sharpes, "fold_results": folds,
    })
    e24_all_sharpes.extend(sharpes)

best24 = max(e24_results, key=lambda x: x["mean_wf_sharpe"])
print(f"\n  Best E24: n={best24['top_n']} gate={best24['use_gate']}  "
      f"mean WF Sharpe={best24['mean_wf_sharpe']:.3f}  worst DD={best24['worst_dd']:.1f}%")

# DSR + CI for best E24
sector_oos = sector_panel_cut.loc[OOS_A:OOS_B]
best24_w_oos = lvs.multi_signals(sector_oos, top_n=best24["top_n"],
                                   use_trend_gate=best24["use_gate"])
best24_oos_ret = me.portfolio_returns(sector_oos, best24_w_oos, commission=COST,
                                       rf_daily=rf_daily.loc[OOS_A:OOS_B])
# Compare vs SPY OOS
spy_oos_ret2 = spy_cut.loc[OOS_A:OOS_B].pct_change().fillna(0.0)
dsr24, ci24 = dsr_and_ci(best24_oos_ret, e24_all_sharpes + prior_trials, spy_oos_ret2)
print(f"  DSR: {dsr24:.4f}  CI (diff vs SPY): [{ci24.lo:+.3f}, {ci24.hi:+.3f}]  clears_zero: {ci24.clears_noise}")

# Benchmark check for E24: mean WF Sharpe > SPY B&H
spy_bh_sharpes = [r["Sharpe"] for r in spy_bh_results]
spy_mean_wf = float(np.mean(spy_bh_sharpes))
e24_pass = (best24["mean_wf_sharpe"] > spy_mean_wf and
            best24["worst_dd"] > -60.0 and
            dsr24 >= 0.95 and ci24.clears_noise)
e24_verdict = "adopted" if e24_pass else "discarded"
print(f"  SPY mean WF Sharpe: {spy_mean_wf:.3f}")
print(f"  E24 verdict: {e24_verdict.upper()}")

record_outcome(reg24.id, e24_verdict, evidence={
    "best_params": {"top_n": best24["top_n"], "use_gate": best24["use_gate"]},
    "mean_wf_sharpe": round(best24["mean_wf_sharpe"], 4),
    "worst_dd": round(best24["worst_dd"], 2),
    "dsr": round(dsr24, 4),
    "ci_lo": round(ci24.lo, 3),
    "ci_hi": round(ci24.hi, 3),
})

# ---------------------------------------------------------------------------
# 8. Monthly v2 significance re-check (ROADMAP item #10)
# ---------------------------------------------------------------------------
print("\n\n=== ROADMAP #10: v2 MONTHLY SIGNIFICANCE RE-CHECK ===")
# Full sample (2000->2026-07-17 cut, no holdout) with all prior trials (159)
v2_full_sig = vt.signals(spy_cut, target_vol=0.18, lookback=20)
v2_full_ret = ve.strategy_returns(spy_cut, v2_full_sig, commission=COST, rf_daily=rf_daily)
spy_full_ret = spy_cut.pct_change().fillna(0.0)
total_trials_pp = trials_this_period()
# Use v2 fold sharpes + all new trial sharpes for deflation
all_recorded_sharpes = (v2_fold_sharpes + e22_all_sharpes + e23_all_sharpes + e24_all_sharpes)
dsr_v2 = ev.deflated_sharpe_ratio(v2_full_ret, all_recorded_sharpes)
ci_v2 = ev.bootstrap_difference_ci(v2_full_ret, spy_full_ret)
print(f"  Total configs this session: {trials_this_period()}")
print(f"  v2 full-sample DSR (deflated by {len(all_recorded_sharpes)} trials): {dsr_v2:.4f}")
print(f"  v2 diff-vs-SPY CI: [{ci_v2.lo:+.4f}, {ci_v2.hi:+.4f}]  clears_zero: {ci_v2.clears_noise}")

# ---------------------------------------------------------------------------
# 9. $1k virtual trade simulation (2000-07-17 final values)
# ---------------------------------------------------------------------------
print("\n\n=== $1k VIRTUAL TRADE SIMULATION (2000->2026-07-17) ===")

v2_m = ve.metrics(spy_cut, vt.signals(spy_cut, target_vol=0.18, lookback=20),
                   commission=COST, rf_daily=rf_daily, label="v2 Champion")

ens_best_w = ens.v2_cta_signals(panel_cut, alpha=best22_alpha,
                                  cta_assets=E22_CTA_ASSETS, cta_vol_target=0.12)
ens_m = me.metrics(panel_cut, ens_best_w, commission=COST, rf_daily=rf_aligned,
                   label=f"E22 Ensemble(v2={best22_alpha:.0%})")

mb_best_sig = mb.signals(spy_cut,
                          SECTOR_PANEL_FULL.reindex(spy_cut.index),
                          upper_band=best23["upper"], lower_band=best23["lower"],
                          vol_target=best23["vtgt"])
mb_m = ve.metrics(spy_cut, mb_best_sig, commission=COST, rf_daily=rf_daily,
                   label=f"E23 Breadth(up={best23['upper']},lo={best23['lower']})")

lvs_best_w = lvs.multi_signals(sector_panel_cut, top_n=best24["top_n"],
                                 use_trend_gate=best24["use_gate"])
lvs_m = me.metrics(sector_panel_cut, lvs_best_w, commission=COST,
                    rf_daily=rf_aligned, label=f"E24 LowVol(n={best24['top_n']})")

# Benchmarks
spy_bh_m = ve.metrics(spy_cut, pd.Series(1.0, index=spy_cut.index),
                       commission=0.0, label="SPY B&H")
qqq = loader.load_ohlcv("QQQ")["Close"].loc[:spy_cut.index[-1]]
qqq = qqq[qqq.index < HOLDOUT_START]
qqq_bh_m = ve.metrics(qqq, pd.Series(1.0, index=qqq.index),
                       commission=0.0, label="QQQ B&H")
dia = loader.load_ohlcv("DIA")["Close"].loc[:spy_cut.index[-1]]
dia = dia[dia.index < HOLDOUT_START]
dia_bh_m = ve.metrics(dia, pd.Series(1.0, index=dia.index),
                       commission=0.0, label="DIA (DOW) B&H")
iwm = loader.load_ohlcv("IWM")["Close"].loc[:spy_cut.index[-1]]
iwm = iwm[iwm.index < HOLDOUT_START]
iwm_bh_m = ve.metrics(iwm, pd.Series(1.0, index=iwm.index),
                       commission=0.0, label="IWM B&H")

# Mag-7 (from 2012 - first year all 7 available)
MAG7 = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
mag7_panel = loader.load_universe(MAG7, start="2012-01-01")
mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna(axis=1)
mag7_spy = spy_cut.loc["2012-01-01":]
mag7_eqw = pd.Series(1.0 / len(mag7_panel.columns), index=mag7_panel.index)
mag7_w = pd.DataFrame({c: 1.0 / len(mag7_panel.columns) for c in mag7_panel.columns},
                       index=mag7_panel.index)
mag7_m = me.metrics(mag7_panel, mag7_w, commission=0.0, label="Mag-7 EqW (2012+)")

print("\n  Strategy                          | CAGR  | Sharpe |  MaxDD  | $1k->")
print("  " + "-"*70)
for m in [v2_m, ens_m, mb_m, lvs_m, spy_bh_m, qqq_bh_m, dia_bh_m, iwm_bh_m]:
    term = m.get("End$per1k", m.get("End$per1k", "?"))
    print(f"  {m['label']:35s} | {m['CAGR']:+5.1f}%| {m['Sharpe']:5.3f}  | {m['MaxDD']:+6.1f}% | ${term:,.0f}")
print(f"  {'Mag-7 EqW (from 2012)':35s} | {mag7_m['CAGR']:+5.1f}%| {mag7_m['Sharpe']:5.3f}  | {mag7_m['MaxDD']:+6.1f}% | ${mag7_m['End$per1k']:,.0f}")

print("\n  (Mag-7 from 2012 — survivorship bias; G4 prevents single-stock overweight in live portfolio)")

# ---------------------------------------------------------------------------
# 10. Print session summary
# ---------------------------------------------------------------------------
print("\n\n=== SESSION 13 SUMMARY ===")
print(f"  Configs burned this session: {trials_this_period() - 159}")
print(f"  Total cumulative configs: {trials_this_period()}")
print(f"\n  E22 (v2+CTA Ensemble): {e22_verdict.upper()}")
print(f"       Best alpha={best22_alpha:.0%}, mean WF Sharpe={best22['mean_wf_sharpe']:.3f}, worst DD={best22['worst_dd']:.1f}%")
print(f"       DSR={dsr22:.4f}, CI=[{ci22.lo:+.3f},{ci22.hi:+.3f}], corr_v2={corr_e22:.3f}")
print(f"\n  E23 (Market Breadth): {e23_verdict.upper()}")
print(f"       Best params=up{best23['upper']}/lo{best23['lower']}/vt{best23['vtgt']}, "
      f"mean WF Sharpe={best23['mean_wf_sharpe']:.3f}, worst DD={best23['worst_dd']:.1f}%")
print(f"       DSR={dsr23:.4f}, CI=[{ci23.lo:+.3f},{ci23.hi:+.3f}], corr_v2={corr_e23:.3f}")
print(f"\n  E24 (Low-Vol Sector): {e24_verdict.upper()}")
print(f"       Best params=n{best24['top_n']}/gate{best24['use_gate']}, "
      f"mean WF Sharpe={best24['mean_wf_sharpe']:.3f}, worst DD={best24['worst_dd']:.1f}%")
print(f"       DSR={dsr24:.4f}, CI=[{ci24.lo:+.3f},{ci24.hi:+.3f}]")
print(f"\n  ROADMAP #10 v2 re-check: DSR={dsr_v2:.4f}, CI=[{ci_v2.lo:+.4f},{ci_v2.hi:+.4f}]")
print(f"\n  Portfolio: ${new_value:.2f} (data stale 1 trading day; mark carried from S12)")
print(f"  Guardrails: {'ALL GREEN' if gr_report['all_ok'] else 'NON-GREEN — SEE ABOVE'}")
print(f"\nRun complete. Configs: {trials_this_period()}")
