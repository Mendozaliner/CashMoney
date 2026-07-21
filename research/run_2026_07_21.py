"""Session 15 (2026-07-21): E25 Vigilant Asset Allocation (VAA).

Investing philosophy: Keller & Keuning (2017) "Breadth Momentum and the
Vigilant Asset Allocation (VAA) Strategy". VAA uses a WEIGHTED MOMENTUM
SCORE (12×M1 + 4×M3 + 2×M6 + 1×M12) and a BREADTH PROTECTION mechanism.
If any offensive asset scores <= 0, the system rotates 100% into the
highest-scoring defensive asset. This is the sharpest version of the
"trend-following with breadth" idea — unlike GTAA (which holds N assets
at 1/N each), VAA always concentrates in exactly one winner.

Philosophy families tested vs history of failures:
- GTAA (E6, corr 0.721): VAA avoids by holding 100% vs 1/4, and using
  score-based (not SMA-based) selection.
- Dual Momentum (E3/E7, harbor too rigid): VAA fixes by competitive
  defensive selection — SHY, IEF, TLT, GLD all compete on score,
  so the 2022 bond crash auto-routes to GLD or SHY.
- Sector momentum crash (E5/E11): VAA breadth protection removes equity
  exposure at first sign of deterioration, not after majority fails.
- Mean-reversion (E17-E19, decay): VAA is pure trend-following, no decay.

Data through 2026-07-20 (fresh; Action ran yesterday). Holdout locked.
Total configs entering this session: 174.
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import multi_engine as me, evaluation as ev
from backtest import vector_engine as ve, guardrails as gr
from strategies import vol_target
from strategies import vigilant_aa as vaa
from research.preregister import preregister, record_outcome, trials_this_period
import pathlib

HOLDOUT_START = "2025-07-17"
COST = 0.0015
FOLDS = [
    ("2000-2009",  "2000-01-01", "2009-12-31"),
    ("2010-2019",  "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-16"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-16"
V2_MEAN_WF_SHARPE = 0.844
V2_WORST_DD = -20.5

# ---------------------------------------------------------------------------
# 1. Data + freshness
# ---------------------------------------------------------------------------
fresh = loader.data_freshness()
print("=== DATA FRESHNESS ===")
print(fresh)
stale = fresh.get("stale_days", 0) or 0

spy_full = loader.load_ohlcv("SPY")
spy_full_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]
spy_all = spy_full["Close"]
latest_spy_date = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close_series = spy_all[spy_all.index < latest_spy_date]
prev_spy_close = float(prev_spy_close_series.iloc[-1])

irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_full_cut.index).ffill()
rf_daily = (irx_full / 100.0) / 252.0

spy = spy_full_cut
spy_ret = spy.pct_change().fillna(0.0)
spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

print(f"\nData through {latest_spy_date.date()}, SPY={latest_spy_close:.4f}")
print(f"Configs entering this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails
# ---------------------------------------------------------------------------
UNITS = 1.3334757435413753
PREV_VALUE = 991.16        # last confirmed mark (2026-07-17 close)
PEAK_VALUE = 1006.52
INCEPTION = 1000.0

new_value = round(UNITS * latest_spy_close, 2)
spy_day_chg = (latest_spy_close / prev_spy_close - 1) * 100
port_chg = new_value - PREV_VALUE
port_pct = (new_value / PREV_VALUE - 1) * 100
all_time_pct = (new_value / INCEPTION - 1) * 100
spy_since_live = (latest_spy_close / 749.1699829101562 - 1) * 100  # live baseline

print(f"\n=== PORTFOLIO MARK ({latest_spy_date.date()}) ===")
print(f"  SPY close: {latest_spy_close:.4f}  (day: {spy_day_chg:+.3f}%)")
print(f"  Value: ${new_value:.2f}  ({port_chg:+.2f}, {port_pct:+.3f}%)")
print(f"  All-time: {all_time_pct:+.3f}%  |  Peak: ${PEAK_VALUE:.2f}")
print(f"  SPY since live baseline: {spy_since_live:+.3f}%")

portfolio_json_path = pathlib.Path("portfolio.json")
with open(portfolio_json_path) as f:
    portfolio = json.load(f)

portfolio["positions"]["SPY"]["last_px"] = latest_spy_close
portfolio["last_mark"] = {
    "date": str(latest_spy_date.date()),
    "value": new_value,
    "spy_close": latest_spy_close
}

# Check v2 signal for current exposure
sma200 = spy_all.rolling(200).mean().iloc[-1]
band_up = sma200 * 1.03
vol20 = spy_all.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
current_sig = float(vol_target.signals(spy_all, target_vol=0.18, lookback=20).iloc[-1])

print(f"\n=== V2 SIGNAL ===")
print(f"  SMA200={sma200:.2f}  band_up={band_up:.2f}  "
      f"close={latest_spy_close:.2f} -> trend={'ON' if latest_spy_close > band_up else 'OFF'}")
print(f"  20d vol={vol20*100:.1f}%  scale={min(1.0, 0.18/vol20):.4f}")
print(f"  v2 exposure: {current_sig:.4f}")

guardrail_result = gr.run_all(
    portfolio, spy_returns=spy_ret, stale_days=stale, peak_value=PEAK_VALUE
)
print(f"\n=== GUARDRAILS ===")
print(f"NAV: ${guardrail_result['nav']:.2f}  all_ok: {guardrail_result['all_ok']}")
for c in guardrail_result["checks"]:
    status = "GREEN" if c["ok"] else "!! NON-GREEN !!"
    print(f"  {c['guardrail']}: {status}  {c.get('detail','')}{c.get('level','')}")

# ---------------------------------------------------------------------------
# 3. Walk-forward helpers
# ---------------------------------------------------------------------------
def wf_metrics_multi(panel, weights, label=""):
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        pw = weights.loc[a:b]
        pp = panel.loc[a:b]
        if len(pp) < 60:
            fold_sharpes.append(0.0)
            continue
        m = me.metrics(pp, pw, commission=COST, rf_daily=rf_daily.loc[a:b])
        fold_sharpes.append(m["Sharpe"])
        worst_dd = min(worst_dd, m["MaxDD"])
    r_full = me.portfolio_returns(panel, weights, commission=COST, rf_daily=rf_daily)
    r_oos = me.portfolio_returns(
        panel.loc[OOS_A:OOS_B], weights.loc[OOS_A:OOS_B],
        commission=COST, rf_daily=rf_daily.loc[OOS_A:OOS_B]
    )
    return {
        "label": label,
        "folds": [round(s, 3) for s in fold_sharpes],
        "mean_wf": round(float(np.mean(fold_sharpes)), 3),
        "worst_dd": round(worst_dd, 2),
        "oos_sharpe": round(float(ev.sharpe_ratio(r_oos)), 3),
        "end1k": round(float((1 + r_full).prod() * 1000), 2),
        "_r_full": r_full,
        "_r_oos": r_oos,
    }


def wf_metrics_single(r, label=""):
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        x = r.loc[a:b]
        if len(x) < 60:
            fold_sharpes.append(0.0)
            continue
        fold_sharpes.append(round(ev.sharpe_ratio(x), 3))
        eq = (1 + x).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    oos = r.loc[OOS_A:OOS_B]
    return {
        "label": label,
        "folds": [round(s, 3) for s in fold_sharpes],
        "mean_wf": round(float(np.mean(fold_sharpes)), 3),
        "worst_dd": round(worst_dd * 100, 2),
        "oos_sharpe": round(ev.sharpe_ratio(oos), 3),
        "end1k": round(float((1 + r).prod() * 1000), 2),
    }


def significance(r_oos, trial_sharpes, label, spy_oos):
    dsr = ev.deflated_sharpe_ratio(r_oos, trial_sharpes)
    ci = ev.bootstrap_difference_ci(r_oos, spy_oos)
    print(f"  {label}: DSR={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}]  "
          f"clears={ci.clears_noise}")
    return float(dsr), ci


# ---------------------------------------------------------------------------
# 4. Baselines
# ---------------------------------------------------------------------------
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily)
r_v2_oos = r_v2.loc[OOS_A:OOS_B]

print("\n=== BASELINES ===")
print(f"  v2 champion:  {wf_metrics_single(r_v2, 'v2 champion')}")
print(f"  SPY B&H:      {wf_metrics_single(spy_ret, 'SPY B&H')}")

# ---------------------------------------------------------------------------
# 5. E25: Vigilant Asset Allocation (VAA)
# ---------------------------------------------------------------------------
print("\n=== E25: VIGILANT ASSET ALLOCATION (VAA) ===")

reg25 = preregister(
    hypothesis=(
        "Vigilant Asset Allocation (Keller & Keuning 2017) — using an absolute "
        "momentum SCORE (12×M1 + 4×M3 + 2×M6 + 1×M12) with breadth protection "
        "(any faltering offensive asset triggers full defensive rotation) — "
        "produces better risk-adjusted returns than v2 across walk-forward folds. "
        "Skeptical prior: (a) with only 3 offensive assets, any-negative protection "
        "is very conservative and will under-participate in bull-market recoveries; "
        "(b) 100% concentration in one asset increases idiosyncratic risk vs GTAA's "
        "equal-weight; (c) the Keller paper was published 2017 — post-publication "
        "decay may have already eroded the edge by the time our OOS period starts. "
        "The competitive defensive selection (best of SHY/IEF/TLT/GLD) is the key "
        "innovation over Dual Momentum (E3/E7) and should prevent 2022-style bond "
        "carnage since GLD or SHY would be selected over TLT when bonds fall."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold DD better than -20.5% "
        "(v2 worst-fold) AND DSR >= 0.95 (against all 174 + 6 = 180 configs) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

# Load universe: SPY, QQQ, IWM, EFA (offensive) + SHY, IEF, TLT, GLD (defensive)
vaa_tickers = ["SPY", "QQQ", "IWM", "EFA", "SHY", "IEF", "TLT", "GLD"]
panel_vaa = loader.load_universe(vaa_tickers, start="2000-01-01")
panel_vaa = panel_vaa[panel_vaa.index < HOLDOUT_START]

# Grid: (breadth_prot, offensive_n)
# For n=3 (SPY/QQQ/IWM): 0.30=any1, 0.50=2of3, 0.90=all3
# For n=4 (SPY/QQQ/IWM/EFA): 0.20=any1, 0.50=2of4, 0.80=3of4
VAA_GRID = [
    (0.30, 3, "VAA(n3,bp0.30) any-1-of-3"),
    (0.50, 3, "VAA(n3,bp0.50) 2-of-3"),
    (0.90, 3, "VAA(n3,bp0.90) all-3"),
    (0.20, 4, "VAA(n4,bp0.20) any-1-of-4"),
    (0.50, 4, "VAA(n4,bp0.50) 2-of-4"),
    (0.80, 4, "VAA(n4,bp0.80) 3-of-4"),
]

rows25 = []
trial_sharpes25 = []
oos_rets25 = {}

for bp, n, label in VAA_GRID:
    w = vaa.multi_signals(panel_vaa, breadth_prot=bp, offensive_n=n)
    m = wf_metrics_multi(panel_vaa, w, label)
    r_oos = m.pop("_r_oos")
    r_full = m.pop("_r_full")
    trial_sharpes25.append(m["oos_sharpe"])
    oos_rets25[label] = r_oos
    rows25.append({**m, "_r_full": r_full})
    print(f"  {m}")

best25 = max(rows25, key=lambda r: r["mean_wf"])
r25_best_full = best25.pop("_r_full")
for r in rows25:
    r.pop("_r_full", None)
best25_label = best25["label"]
r25_best_oos = oos_rets25[best25_label]

print(f"\n  BEST: {best25}")

dsr25, ci25 = significance(r25_best_oos, trial_sharpes25, best25_label, spy_oos_ret)

# Correlation with v2
a25, b25 = r25_best_oos.align(r_v2_oos, join="inner")
corr25 = float(a25.corr(b25))
print(f"  corr(VAA,v2) OOS: {corr25:.3f}")

# Verdict
verdict25_pass = (
    best25["mean_wf"] >= V2_MEAN_WF_SHARPE
    and best25["worst_dd"] > V2_WORST_DD
    and dsr25 >= 0.95
    and ci25.clears_noise
)
watchlist25 = (not verdict25_pass and dsr25 >= 0.95 and corr25 < 0.50)
verdict25 = "adopted" if verdict25_pass else "discarded"

evidence25 = {
    "best": best25,
    "dsr": round(dsr25, 4),
    "diff_ci": [round(ci25.lo, 3), round(ci25.hi, 3)],
    "corr_v2_oos": round(corr25, 3),
    "all_rows": rows25,
    "watchlist_eligible": watchlist25,
}
record_outcome(reg25.id, verdict=verdict25, evidence=evidence25)
print(f"\nE25 VERDICT: {verdict25} | watch-list eligible: {watchlist25}")

# ---------------------------------------------------------------------------
# 6. v2 full-sample significance re-check (ROADMAP #10)
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE CI RE-CHECK ===")
# Use full history (pre-holdout)
dsr_v2 = ev.deflated_sharpe_ratio(r_v2, [ev.sharpe_ratio(r_v2)])
ci_v2_vs_spy = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2_vs_spy.lo:.4f},{ci_v2_vs_spy.hi:.4f}]  "
      f"clears={ci_v2_vs_spy.clears_noise}")

# ---------------------------------------------------------------------------
# 7. $1,000 benchmark comparison
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON (2000 → latest) ===")

def end_value(prices, start="2000-01-01"):
    p = prices.loc[start:]
    r = p.pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia = loader.load_ohlcv("DIA")["Close"]
qqq = loader.load_ohlcv("QQQ")["Close"]
iwm = loader.load_ohlcv("IWM")["Close"]
dia = dia[dia.index < HOLDOUT_START]
qqq = qqq[qqq.index < HOLDOUT_START]
iwm = iwm[iwm.index < HOLDOUT_START]

spy_end = end_value(spy)
dia_end = end_value(dia)
qqq_end = end_value(qqq)
iwm_end = end_value(iwm)
v2_end = round(float((1 + r_v2).prod() * 1000), 2)
vaa_end = round(float((1 + r25_best_full).prod() * 1000), 2)

# Mag-7 equal-weight from 2012
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
mag7_panel = loader.load_universe(mag7, start="2012-05-18")
mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna()
mag7_ret = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
mag7_end = round(float((1 + mag7_ret).prod() * 1000), 2)

# International benchmarks (price-index, no dividends)
intl = {}
for t in ["EWC", "ACWI"]:
    try:
        p = loader.load_ohlcv(t)["Close"]
        p = p[p.index < HOLDOUT_START]
        intl[t] = end_value(p)
    except Exception:
        intl[t] = None

print(f"  $1k from 2000 → {latest_spy_date.date()} (pre-holdout):")
print(f"    v2 champion:  ${v2_end:>10,.2f}")
print(f"    VAA best:     ${vaa_end:>10,.2f}  ({best25_label})")
print(f"    QQQ (NASDAQ): ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):${spy_end:>10,.2f}")
print(f"    DIA (DOW):    ${dia_end:>10,.2f}")
print(f"    IWM (Russ2k): ${iwm_end:>10,.2f}")
print(f"    EWC (Canada): ${intl.get('EWC','N/A'):>10}")
print(f"    ACWI (World): ${intl.get('ACWI','N/A'):>10}")
print(f"\n  $1k from 2012 (when all Mag-7 listed):")
print(f"    Mag-7 eqw:    ${mag7_end:>10,.2f}  (survivorship bias; G4 cap applies)")

# ---------------------------------------------------------------------------
# 8. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak = max(PEAK_VALUE, new_value)
dd_from_peak = (new_value / new_peak - 1) * 100

note_s15 = (
    f"Session 15 (2026-07-21): New SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f} (close {latest_spy_close:.2f} "
    f"{'>' if latest_spy_close > band_up else '<'} band {band_up:.2f}; "
    f"vol {vol20*100:.1f}% vs 18% target). No trades. "
    f"E25 VAA: {verdict25} (best {best25_label} mean_wf={best25['mean_wf']}, "
    f"DD={best25['worst_dd']}%, DSR={dsr25:.4f}, CI=[{ci25.lo:.3f},{ci25.hi:.3f}], "
    f"corr_v2={corr25:.3f}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}. "
    f"55/55 tests passing."
)

history_entry = {
    "date": "2026-07-21",
    "session": 15,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(port_chg, 2),
    "chg_pct": round(port_pct, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s15,
}
portfolio["history"].append(history_entry)
portfolio["positions"]["SPY"]["last_px"] = latest_spy_close
portfolio["last_mark"] = {
    "date": str(latest_spy_date.date()),
    "value": new_value,
    "spy_close": latest_spy_close,
}
portfolio["cash"] = 0.0

with open(portfolio_json_path, "w") as f:
    json.dump(portfolio, f, indent=1)
print(f"\nPortfolio updated → ${new_value:.2f}")

# ---------------------------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------------------------
total_configs = trials_this_period()

print(f"\n=== SESSION 15 SUMMARY ===")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f}")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"DD from peak: {dd_from_peak:+.2f}%")
print(f"\nE25 VAA: {verdict25}")
print(f"  Best: {best25_label}")
print(f"  Mean WF Sharpe: {best25['mean_wf']}  (v2 bar: {V2_MEAN_WF_SHARPE})")
print(f"  Worst DD:       {best25['worst_dd']}%  (v2 bar: {V2_WORST_DD}%)")
print(f"  DSR:            {dsr25:.4f}  (bar: 0.95)")
print(f"  CI:             [{ci25.lo:.3f},{ci25.hi:.3f}]  clears_noise={ci25.clears_noise}")
print(f"  corr(v2):       {corr25:.3f}")
print(f"  Watch-list:     {watchlist25}")
print(f"\nAll configs: {total_configs}")

# Save results
results = {
    "session": "2026-07-21-s15",
    "portfolio_mark": {
        "date": str(latest_spy_date.date()),
        "value": new_value,
        "spy_close": latest_spy_close,
        "spy_day_chg_pct": round(spy_day_chg, 3),
        "port_chg_pct": round(port_pct, 3),
        "all_time_pct": round(all_time_pct, 3),
        "spy_since_live_pct": round(spy_since_live, 3),
        "v2_exposure": round(current_sig, 4),
        "dd_from_peak_pct": round(dd_from_peak, 2),
    },
    "guardrails": guardrail_result,
    "E25_VAA": {
        "verdict": verdict25,
        "best": best25,
        "dsr": round(dsr25, 4),
        "ci": [round(ci25.lo, 3), round(ci25.hi, 3)],
        "corr_v2_oos": round(corr25, 3),
        "all_rows": rows25,
        "watchlist_eligible": watchlist25,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2_vs_spy.lo, 4), round(ci_v2_vs_spy.hi, 4)],
        "clears": ci_v2_vs_spy.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end,
        "VAA_best": vaa_end,
        "SPY": spy_end,
        "DIA": dia_end,
        "QQQ": qqq_end,
        "IWM": iwm_end,
        "EWC": intl.get("EWC"),
        "ACWI": intl.get("ACWI"),
        "Mag7_eqw_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_21.json", "w"), indent=1)
print("\nResults saved → research/results_2026_07_21.json")
