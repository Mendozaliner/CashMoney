"""Session 12 (2026-07-18): E20 Multi-Asset CTA Trend, E21 Seasonal Effect.

Two new investing-philosophy families not yet explored:
  E20: CTA/Managed-Futures replication -- apply vol-targeted trend to each of
       SPY/TLT/GLD (and variants) simultaneously; equal-risk-budget weighting.
  E21: Halloween / Sell-in-May seasonal overlay on v2's signal.

Data fresh through 2026-07-17. Holdout locked from 2025-07-17.
Charter queue exhausted (9/9 families, 149 configs entering this session).
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, multi_engine as me
from strategies import vol_target, seasonal as seas
from strategies import cta_trend as cta
from research.preregister import preregister, record_outcome, trials_this_period
from backtest import guardrails as gr
import pathlib

HOLDOUT_START = "2025-07-17"
COST = 0.0015
FOLDS = [
    ("2000-2009",  "2000-01-01", "2009-12-31"),
    ("2010-2019",  "2010-01-01", "2019-12-31"),
    ("2020-2025H", "2020-01-01", "2025-07-16"),
]
OOS_A, OOS_B = "2020-01-01", "2025-07-16"
V2_MEAN_WF_SHARPE = 0.851   # champion bar to beat (updated best from s7)
V2_WORST_DD = -20.5          # worst-fold DD for v2

# ---------------------------------------------------------------------------
# 1. Data + freshness
# ---------------------------------------------------------------------------
fresh = loader.data_freshness()
print("=== DATA FRESHNESS ===")
print(fresh)
stale = fresh.get("stale_days", 0) or 0

spy_full = loader.load_ohlcv("SPY")
spy_full_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]
spy_ohlc_full = spy_full[spy_full.index < HOLDOUT_START]

# latest mark date for portfolio update
spy_all = spy_full["Close"]
latest_spy_date = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close = float(spy_all.iloc[-2])

irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_full_cut.index).ffill()
rf_daily_full = (irx_full / 100.0) / 252.0

spy = spy_full_cut
irx = irx_full
rf_daily = rf_daily_full

spy_ret = spy.pct_change().fillna(0.0)

print(f"\nData through {spy_all.index[-1].date()}, SPY={latest_spy_close:.2f}")
print(f"Configs before this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails
# ---------------------------------------------------------------------------
UNITS = 1.333476
prev_value = 1001.07   # last mark (2026-07-16 close)
new_value = round(UNITS * latest_spy_close, 2)
peak_value = 1006.52
spy_day_chg = (latest_spy_close / prev_spy_close - 1) * 100
port_chg = new_value - prev_value
port_pct = (new_value / prev_value - 1) * 100
all_time_pct = (new_value / 1000.0 - 1) * 100

print(f"\n=== PORTFOLIO MARK ({latest_spy_date.date()}) ===")
print(f"  SPY close: {latest_spy_close:.2f}  (day: {spy_day_chg:+.3f}%)")
print(f"  Value: ${new_value:.2f}  ({port_chg:+.2f}, {port_pct:+.3f}%)")
print(f"  All-time: {all_time_pct:+.3f}%  |  Peak: ${peak_value:.2f}")

portfolio_json_path = pathlib.Path("portfolio.json")
with open(portfolio_json_path) as f:
    portfolio = json.load(f)

# Update portfolio for guardrails
portfolio["positions"]["SPY"]["last_px"] = latest_spy_close
portfolio["last_mark"] = {"date": str(latest_spy_date.date()),
                          "value": new_value, "spy_close": latest_spy_close}

guardrail_result = gr.run_all(
    portfolio,
    spy_returns=spy_ret,
    stale_days=stale,
    peak_value=peak_value
)
print(f"\n=== GUARDRAILS ===")
print(f"NAV: ${guardrail_result['nav']:.2f}  all_ok: {guardrail_result['all_ok']}")
for c in guardrail_result["checks"]:
    ok = "GREEN" if c["ok"] else "!! NON-GREEN !!"
    print(f"  {c['guardrail']}: {ok}  {c.get('detail','')}{c.get('level','')}")

# ---------------------------------------------------------------------------
# 3. Walk-forward helpers
# ---------------------------------------------------------------------------
def wf_metrics_single(r, spy_ret_series, label=""):
    """Walk-forward for single-asset strategies (vector_engine returns)."""
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        x = r.loc[a:b]
        if len(x) < 60:
            fold_sharpes.append(0.0); continue
        fold_sharpes.append(round(ev.sharpe_ratio(x), 3))
        eq = (1 + x).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    oos = r.loc[OOS_A:OOS_B]
    spy_oos = spy_ret_series.reindex(oos.index).fillna(0.0)
    return {"label": label, "folds": fold_sharpes,
            "mean_wf": round(float(np.mean(fold_sharpes)), 3),
            "worst_dd": round(worst_dd * 100, 2),
            "oos_sharpe": round(ev.sharpe_ratio(oos), 3),
            "end1k": round(float((1 + r).prod() * 1000), 2)}

def wf_metrics_multi(panel, weights, label=""):
    """Walk-forward for multi-asset strategies (multi_engine)."""
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        pw = weights.loc[a:b]; pp = panel.loc[a:b]
        if len(pp) < 60:
            fold_sharpes.append(0.0); continue
        m = me.metrics(pp, pw, commission=COST, rf_daily=rf_daily.loc[a:b])
        fold_sharpes.append(m["Sharpe"]); worst_dd = min(worst_dd, m["MaxDD"])
    r_full = me.portfolio_returns(panel, weights, commission=COST, rf_daily=rf_daily)
    r_oos = me.portfolio_returns(panel.loc[OOS_A:OOS_B], weights.loc[OOS_A:OOS_B],
                                 commission=COST, rf_daily=rf_daily.loc[OOS_A:OOS_B])
    return {"label": label, "folds": [round(s,3) for s in fold_sharpes],
            "mean_wf": round(float(np.mean(fold_sharpes)), 3),
            "worst_dd": round(worst_dd, 2),
            "oos_sharpe": round(float(ev.sharpe_ratio(r_oos)), 3),
            "end1k": round(float((1 + r_full).prod() * 1000), 2),
            "_r_full": r_full, "_r_oos": r_oos}

def significance(r_oos, trial_sharpes, label, spy_oos):
    dsr = ev.deflated_sharpe_ratio(r_oos, trial_sharpes)
    ci = ev.bootstrap_difference_ci(r_oos, spy_oos)
    print(f"  {label}: DSR={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}]  "
          f"clears={ci.clears_noise}")
    return float(dsr), ci

spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

# Baseline metrics
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2 = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily)
v2_m = wf_metrics_single(r_v2, spy_ret, "v2 champion")
print(f"\n=== BASELINES ===")
print(f"  v2 champion: {v2_m}")
print(f"  SPY B&H:     {wf_metrics_single(spy_ret, spy_ret, 'SPY B&H')}")

# ---------------------------------------------------------------------------
# 4. E20: Multi-Asset CTA Trend Following
# ---------------------------------------------------------------------------
print("\n=== E20: MULTI-ASSET CTA TREND FOLLOWING ===")
reg20 = preregister(
    hypothesis=(
        "Applying v2's vol-targeted trend filter to multiple uncorrelated asset "
        "classes simultaneously (equities SPY, long bonds TLT, gold GLD, "
        "international EFA) with equal-risk-budget weighting produces better "
        "risk-adjusted returns than single-asset v2 by capturing 'crisis alpha' "
        "during equity bear markets when bonds or gold are in uptrends. Skeptical "
        "prior: unlevered multi-asset trend lags SPY on raw return in bull markets "
        "(Asness 2012); the benefit is Sharpe improvement, not CAGR. Benchmark: "
        "AQR Managed Futures (AQMRX) historically Sharpe ~0.5-0.8 before costs."
    ),
    success_criteria=(
        "mean WF Sharpe >= v2's 0.844 AND OOS MaxDD shallower than -20% AND "
        "DSR >= 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary bar if CI straddles zero: corr to v2 < 0.50 (same watch-list "
        "condition as RP and PP) to qualify as an ensemble sleeve."
    ),
    grid_size=6, primary_metric="sharpe"
)

ASSET_SETS = [
    ("SPY/TLT/GLD",     ["SPY", "TLT", "GLD"]),
    ("SPY/IEF/GLD",     ["SPY", "IEF", "GLD"]),
    ("SPY/TLT/GLD/EFA", ["SPY", "TLT", "GLD", "EFA"]),
]
VOL_TARGETS_CTA = [0.12, 0.18]

panel_all = loader.load_universe(
    ["SPY", "TLT", "IEF", "GLD", "EFA"],
    start="2000-01-01"
)
panel_all = panel_all[panel_all.index < HOLDOUT_START]

rows20, trial_sharpes20 = [], []
oos_rets20 = {}

for asset_label, asset_list in ASSET_SETS:
    panel = panel_all[asset_list].copy()
    for vt in VOL_TARGETS_CTA:
        label = f"CTA({asset_label},vt{vt})"
        w = cta.multi_signals(panel, assets=asset_list, vol_target=vt,
                              sma_window=200, band=0.03, vol_window=20,
                              normalize=False)
        m = wf_metrics_multi(panel, w, label)
        r_oos = m.pop("_r_oos"); r_full = m.pop("_r_full")
        trial_sharpes20.append(m["oos_sharpe"])
        oos_rets20[label] = r_oos
        rows20.append({**m, "_r_full": r_full})
        print(m)

best20 = max(rows20, key=lambda r: r["mean_wf"])
r20_best_full = best20.pop("_r_full")
for r in rows20:
    r.pop("_r_full", None)
best20_label = best20["label"]
r20_best_oos = oos_rets20[best20_label]

dsr20, ci20 = significance(r20_best_oos, trial_sharpes20, best20_label, spy_oos_ret)

# Correlation with v2
r_v2_oos = r_v2.loc[OOS_A:OOS_B]
a20, b20 = r20_best_oos.align(r_v2_oos, join="inner")
corr20 = float(a20.corr(b20))
print(f"  corr(CTA,v2) OOS: {corr20:.3f}")

verdict20_pass = (best20["mean_wf"] >= 0.844 and best20["worst_dd"] > -20.0
                  and dsr20 >= 0.95 and ci20.clears_noise)
watchlist20 = (not verdict20_pass and corr20 < 0.50 and dsr20 >= 0.95)
verdict20 = "adopted" if verdict20_pass else "discarded"
evidence20 = {"best": best20, "dsr": round(dsr20, 4),
              "diff_ci": [round(ci20.lo, 3), round(ci20.hi, 3)],
              "corr_v2_oos": round(corr20, 3), "all_rows": rows20,
              "watchlist_eligible": watchlist20}
record_outcome(reg20.id, verdict=verdict20, evidence=evidence20)
print(f"E20 VERDICT: {verdict20} | watch-list eligible: {watchlist20}")

# ---------------------------------------------------------------------------
# 5. E21: Seasonal / Halloween Effect
# ---------------------------------------------------------------------------
print("\n=== E21: SEASONAL / HALLOWEEN EFFECT ===")
reg21 = preregister(
    hypothesis=(
        "Restricting v2's trend exposure to the seasonally strong half of the year "
        "(November through April, the 'Halloween window') and reducing to "
        "off_season_scale in May-October improves Sharpe by avoiding the historically "
        "weaker summer period. The effect has been documented since Bouman & Jacobsen "
        "(2002) in 36 countries and replicated post-publication. Skeptical prior: "
        "the 2010-2020 US bull market ran through summer months frequently; the "
        "effect may have decayed; costs of market-timing amplify decay."
    ),
    success_criteria=(
        "mean WF Sharpe >= v2's 0.844 AND OOS MaxDD shallower than -20% AND "
        "DSR >= 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0."
    ),
    grid_size=4, primary_metric="sharpe"
)

SEASONAL_GRID = [
    # (good_months, off_season_scale, label)
    ((11,12,1,2,3,4), 0.0,  "Seas(Nov-Apr,out=0)"),
    ((11,12,1,2,3,4), 0.3,  "Seas(Nov-Apr,out=0.3)"),
    ((10,11,12,1,2,3,4), 0.0,  "Seas(Oct-Apr,out=0)"),
    ((10,11,12,1,2,3,4), 0.3,  "Seas(Oct-Apr,out=0.3)"),
]

rows21, trial_sharpes21 = [], []
oos_rets21 = {}

for good_months, off_scale, label in SEASONAL_GRID:
    sig = seas.signals(spy, good_months=good_months, off_season_scale=off_scale)
    r = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m = wf_metrics_single(r, spy_ret, label)
    trial_sharpes21.append(m["oos_sharpe"])
    oos_rets21[label] = r.loc[OOS_A:OOS_B]
    rows21.append(m)
    print(m)

best21 = max(rows21, key=lambda r: r["mean_wf"])
r21_best_oos = oos_rets21[best21["label"]]

dsr21, ci21 = significance(r21_best_oos, trial_sharpes21, best21["label"], spy_oos_ret)

a21, b21 = r21_best_oos.align(r_v2_oos, join="inner")
corr21 = float(a21.corr(b21))
print(f"  corr(Seasonal,v2) OOS: {corr21:.3f}")

verdict21_pass = (best21["mean_wf"] >= 0.844 and best21["worst_dd"] > -20.0
                  and dsr21 >= 0.95 and ci21.clears_noise)
verdict21 = "adopted" if verdict21_pass else "discarded"
evidence21 = {"best": best21, "dsr": round(dsr21, 4),
              "diff_ci": [round(ci21.lo, 3), round(ci21.hi, 3)],
              "corr_v2_oos": round(corr21, 3), "all_rows": rows21}
record_outcome(reg21.id, verdict=verdict21, evidence=evidence21)
print(f"E21 VERDICT: {verdict21}")

# ---------------------------------------------------------------------------
# 6. $1,000 benchmark comparison (full history)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON (2000 -> latest) ===")

# SPY and DIA (DOW)
dia = loader.load_ohlcv("DIA")["Close"]
qqq = loader.load_ohlcv("QQQ")["Close"]
dia = dia[dia.index < HOLDOUT_START]
qqq = qqq[qqq.index < HOLDOUT_START]

def end_value(prices, start="2000-01-01"):
    p = prices.loc[start:]
    r = p.pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

spy_end = end_value(spy)
dia_end = end_value(dia)
qqq_end = end_value(qqq)
v2_end  = round(float((1 + r_v2).prod() * 1000), 2)

# Mag-7 (equal-weight, available from earliest common date ~2012 for META)
mag7_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
mag7_panel = loader.load_universe(mag7_tickers, start="2000-01-01")
mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START]
mag7_all = mag7_panel.dropna(how="all")
mag7_ret = mag7_all.pct_change().fillna(0.0)
mag7_eq_ret = mag7_ret.mean(axis=1)
mag7_end_full = round(float((1 + mag7_eq_ret).prod() * 1000), 2)

# Mag-7 from 2012 (when META listed and all 7 are present)
mag7_2012 = mag7_panel.loc["2012-05-18":].dropna()
mag7_ret_2012 = mag7_2012.pct_change().fillna(0.0).mean(axis=1)
mag7_end_2012 = round(float((1 + mag7_ret_2012).prod() * 1000), 2)

# SPY from 2012 for apple-to-apple Mag-7 comparison
spy_2012 = spy.loc["2012-05-18":].pct_change().fillna(0.0)
spy_end_2012 = round(float((1 + spy_2012).prod() * 1000), 2)
v2_2012 = r_v2.loc["2012-05-18":]
v2_end_2012 = round(float((1 + v2_2012).prod() * 1000), 2)

# Best CTA full-sample
r20_full_idx = r20_best_full.index
cta_end = round(float((1 + r20_best_full).prod() * 1000), 2)

print(f"  $1k from 2000->latest:")
print(f"    v2 champion:  ${v2_end:>10,.2f}")
print(f"    SPY (DOW):    ${dia_end:>10,.2f}  (DIA)")
print(f"    S&P 500:      ${spy_end:>10,.2f}  (SPY)")
print(f"    NASDAQ:       ${qqq_end:>10,.2f}  (QQQ)")
print(f"    CTA (best):   ${cta_end:>10,.2f}  ({best20_label})")
print(f"\n  $1k from 2012 (when all Mag-7 listed):")
print(f"    SPY:          ${spy_end_2012:>10,.2f}")
print(f"    v2:           ${v2_end_2012:>10,.2f}")
print(f"    Mag-7 eqw:    ${mag7_end_2012:>10,.2f}")

# ---------------------------------------------------------------------------
# 7. V2 exposure check for current portfolio
# ---------------------------------------------------------------------------
spy_latest = spy_all
sma200 = spy_latest.rolling(200).mean().iloc[-1]
band_up = sma200 * 1.03
vol20 = spy_latest.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
current_sig = vol_target.signals(spy_latest, target_vol=0.18, lookback=20).iloc[-1]
print(f"\n=== V2 SIGNAL (CURRENT) ===")
print(f"  SPY latest: {spy_latest.iloc[-1]:.2f}")
print(f"  SMA200: {sma200:.2f}  band_up: {band_up:.2f}")
print(f"  20d vol: {vol20:.4f} ann ({vol20*100:.1f}%)")
print(f"  v2 signal: {current_sig:.4f} (target_vol=0.18; scale={min(1,0.18/vol20):.4f})")

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
print("\n=== SESSION 12 SUMMARY ===")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY day change: {spy_day_chg:+.3f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"\nE20 CTA:      {verdict20} | best {best20_label} mean_wf={best20['mean_wf']} "
      f"DD={best20['worst_dd']}% DSR={dsr20:.4f} CI=[{ci20.lo:.3f},{ci20.hi:.3f}] "
      f"corr_v2={corr20:.3f}")
print(f"E21 Seasonal: {verdict21} | best {best21['label']} mean_wf={best21['mean_wf']} "
      f"DD={best21['worst_dd']}% DSR={dsr21:.4f} CI=[{ci21.lo:.3f},{ci21.hi:.3f}] "
      f"corr_v2={corr21:.3f}")
print(f"\nConfigs this session: 10  |  Total configs: {trials_this_period()}")
print(f"Champion v2 UNCHANGED (frozen Phase 2 exam track)")

# Save results
results = {
    "session": "2026-07-18-s12",
    "portfolio_mark": {"date": str(latest_spy_date.date()),
                       "value": new_value, "spy_close": latest_spy_close,
                       "day_chg_pct": round(port_pct, 3),
                       "all_time_pct": round(all_time_pct, 3)},
    "guardrails": guardrail_result,
    "E20": {"verdict": verdict20, "best": best20, "dsr": dsr20,
            "ci": [round(ci20.lo,3), round(ci20.hi,3)],
            "corr_v2": round(corr20, 3), "all_rows": rows20,
            "watchlist_eligible": watchlist20},
    "E21": {"verdict": verdict21, "best": best21, "dsr": dsr21,
            "ci": [round(ci21.lo,3), round(ci21.hi,3)],
            "corr_v2": round(corr21, 3), "all_rows": rows21},
    "benchmarks_1k_from_2000": {
        "v2": v2_end, "SPY": spy_end, "DIA_DOW": dia_end,
        "QQQ": qqq_end, "CTA_best": cta_end},
    "benchmarks_1k_from_2012": {
        "SPY": spy_end_2012, "v2": v2_end_2012, "Mag7_eqw": mag7_end_2012},
    "total_configs": trials_this_period(),
}
json.dump(results, open("research/results_2026_07_18.json", "w"), indent=1)
print("\nResults saved -> research/results_2026_07_18.json")
