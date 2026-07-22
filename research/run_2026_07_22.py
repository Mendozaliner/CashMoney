"""Session 16 (2026-07-22): E26 Turtle Trend + E27 Defensive Asset Allocation.

Two new investing philosophies tested for the first time in this research desk:

E26 — TURTLE TREND (Donchian Channel Breakout):
  Richard Dennis & William Eckhardt's 1983 Turtle Trading System 2.
  Entry: close > N-day channel high. Exit: close < (N/2)-day channel low.
  Vol-targeting overlay (same as v2 champion).
  Key diff from SMA200: responds to actual price extremes, not lagging averages.
  Academic basis: Faith (2003), Baz et al. (2015), Hurst/Ooi/Pedersen (2017).

E27 — DEFENSIVE ASSET ALLOCATION (DAA, Canary Universe):
  Keller & Keuning (2018) update to VAA (E25).
  Key innovation: SEPARATE canary universe (EEM, AGG) watches for recession risk
  INDEPENDENTLY from the tradeable universe. If canary assets trend negative →
  rotate defensively even if SPY/QQQ look fine. Competitive defensive selection
  (best of SHY/IEF/TLT/GLD by 13612W score) prevents the 2022 bond crash trap.
  Lesson from E25 (VAA): breadth protection inside the tradeable universe is too slow.

Data through 2026-07-21 (fresh; GitHub Action ran 2026-07-22 00:55 UTC).
Holdout locked at 2025-07-17. Total configs entering this session: 180.
"""
import sys, json
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import multi_engine as me, evaluation as ev
from backtest import vector_engine as ve, guardrails as gr
from strategies import vol_target
from strategies import turtle_trend as tt
from strategies import daa
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
stale = fresh.get("stale_days", 0) or 0
print(f"  Newest close: {fresh.get('newest_close')}  stale_days: {stale}")

spy_full   = loader.load_ohlcv("SPY")
spy_full_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]
spy_all    = spy_full["Close"]
latest_spy_date  = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close   = float(spy_all[spy_all.index < latest_spy_date].iloc[-1])

irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_full_cut.index).ffill()
rf_daily = (irx_full / 100.0) / 252.0

spy     = spy_full_cut
spy_ret = spy.pct_change().fillna(0.0)
spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

print(f"  Data through {latest_spy_date.date()}, SPY={latest_spy_close:.4f}")
print(f"  Configs entering this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails
# ---------------------------------------------------------------------------
UNITS      = 1.3334757435413753
PREV_VALUE = 989.56
PEAK_VALUE = 1006.52
INCEPTION  = 1000.0

new_value    = round(UNITS * latest_spy_close, 2)
spy_day_chg  = (latest_spy_close / prev_spy_close - 1) * 100
port_chg     = new_value - PREV_VALUE
port_pct     = (new_value / PREV_VALUE - 1) * 100
all_time_pct = (new_value / INCEPTION - 1) * 100
spy_since_live = (latest_spy_close / 749.1699829101562 - 1) * 100

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

sma200    = spy_all.rolling(200).mean().iloc[-1]
band_up   = sma200 * 1.03
vol20     = spy_all.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
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
    r_oos  = me.portfolio_returns(
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


def significance(r_oos, trial_sharpes, label, spy_oos):
    dsr = ev.deflated_sharpe_ratio(r_oos, trial_sharpes)
    ci  = ev.bootstrap_difference_ci(r_oos, spy_oos)
    print(f"  {label}: DSR={dsr:.4f}  diff-CI=[{ci.lo:.3f},{ci.hi:.3f}]  "
          f"clears={ci.clears_noise}")
    return float(dsr), ci


# ---------------------------------------------------------------------------
# 4. Baselines
# ---------------------------------------------------------------------------
sig_v2 = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2   = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily)
r_v2_oos = r_v2.loc[OOS_A:OOS_B]

print("\n=== BASELINES ===")
v2_m   = wf_metrics_single(r_v2, "v2 champion")
spy_m  = wf_metrics_single(spy_ret, "SPY B&H")
print(f"  v2 champion:  {v2_m}")
print(f"  SPY B&H:      {spy_m}")

# ---------------------------------------------------------------------------
# 5. E26: Turtle Trend (Donchian Channel Breakout)
# ---------------------------------------------------------------------------
print("\n=== E26: TURTLE TREND (DONCHIAN CHANNEL) ===")

reg26 = preregister(
    hypothesis=(
        "Turtle Trading (Dennis & Eckhardt 1983, Faith 2003) via Donchian channel "
        "breakout — entry when close > prior N-day high, exit when close < prior "
        "(N/2)-day low, with vol-target overlay — produces better risk-adjusted "
        "returns than the v2 champion (SMA200/3%-band + vol-target) across "
        "walk-forward folds. "
        "Skeptical prior: (a) channel breakout and SMA200 both identify trend "
        "direction, so correlation to v2 may be high (>0.70); (b) channel entry "
        "is later than SMA200 in a strong uptrend (higher entry price); "
        "(c) the Turtle system's original edge came from 1983-era commodity "
        "futures with wider trends — equity markets post-decimalization are more "
        "efficient. (d) publication decay since 2003 book. The vol-targeting "
        "overlay should mitigate (d) by reducing exposure during high-vol periods."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold DD better than -20.5% "
        "AND DSR >= 0.95 AND diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 < 0.60."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

TURTLE_GRID = [
    (20,  0.15, "Turtle(ch20,vol0.15)"),
    (20,  0.18, "Turtle(ch20,vol0.18)"),
    (55,  0.15, "Turtle(ch55,vol0.15)"),
    (55,  0.18, "Turtle(ch55,vol0.18)"),
    (100, 0.15, "Turtle(ch100,vol0.15)"),
    (100, 0.18, "Turtle(ch100,vol0.18)"),
]

rows26 = []
trial_sharpes26 = []
oos_rets26 = {}

for entry_ch, vt_param, label in TURTLE_GRID:
    sig = tt.signals(spy, entry_channel=entry_ch, vol_target=vt_param)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_metrics_single(r, label)
    trial_sharpes26.append(m["oos_sharpe"])
    oos_rets26[label] = r.loc[OOS_A:OOS_B]
    rows26.append({**m, "_r_full": r})
    print(f"  {m}")

best26 = max(rows26, key=lambda r: r["mean_wf"])
r26_best_full = best26.pop("_r_full")
for r in rows26:
    r.pop("_r_full", None)
best26_label = best26["label"]
r26_best_oos = oos_rets26[best26_label]

print(f"\n  BEST: {best26}")

dsr26, ci26 = significance(r26_best_oos, trial_sharpes26, best26_label, spy_oos_ret)

a26, b26 = r26_best_oos.align(r_v2_oos, join="inner")
corr26 = float(a26.corr(b26))
print(f"  corr(Turtle,v2) OOS: {corr26:.3f}")

verdict26_pass = (
    best26["mean_wf"] >= V2_MEAN_WF_SHARPE
    and best26["worst_dd"] > V2_WORST_DD
    and dsr26 >= 0.95
    and ci26.clears_noise
)
watchlist26 = not verdict26_pass and dsr26 >= 0.95 and corr26 < 0.60
verdict26 = "adopted" if verdict26_pass else "discarded"

evidence26 = {
    "best": best26,
    "dsr": round(dsr26, 4),
    "diff_ci": [round(ci26.lo, 3), round(ci26.hi, 3)],
    "corr_v2_oos": round(corr26, 3),
    "all_rows": rows26,
    "watchlist_eligible": watchlist26,
}
record_outcome(reg26.id, verdict=verdict26, evidence=evidence26)
print(f"\nE26 VERDICT: {verdict26} | watch-list: {watchlist26}")

# ---------------------------------------------------------------------------
# 6. E27: Defensive Asset Allocation (DAA, Canary Universe)
# ---------------------------------------------------------------------------
print("\n=== E27: DEFENSIVE ASSET ALLOCATION (DAA, CANARY UNIVERSE) ===")

reg27 = preregister(
    hypothesis=(
        "Defensive Asset Allocation (Keller & Keuning 2018) — using EEM and AGG "
        "as a canary recession indicator SEPARATE from the tradeable universe — "
        "produces better risk-adjusted returns than v2, by triggering defensive "
        "rotation when leading economic indicators (EEM/AGG) deteriorate, "
        "independently of whether domestic equities (SPY/QQQ) have yet declined. "
        "Key improvement over VAA (E25, discarded): VAA's breadth protection "
        "watches the SAME assets it trades, so it responds slowly. DAA's canary "
        "is a dedicated watchdog, potentially faster. "
        "Skeptical prior: (a) EEM and AGG have been available only from ~2003, "
        "limiting the true OOS history; (b) monthly rebalance may miss fast moves; "
        "(c) VAA already failed (E25); DAA addresses the failure mode but the "
        "structural problem of monthly rebalance lag may persist."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 AND worst-fold DD better than -20.5% AND "
        "DSR >= 0.95 AND diff-vs-SPY CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

daa_tickers = ["SPY", "QQQ", "IWM", "GLD", "SHY", "IEF", "TLT", "EEM", "AGG"]
panel_daa = loader.load_universe(daa_tickers, start="2000-01-01")
panel_daa = panel_daa[panel_daa.index < HOLDOUT_START]

DAA_GRID = [
    (0.5, 3, "DAA(cs0.5,n3)"),
    (0.5, 4, "DAA(cs0.5,n4)"),
    (1.0, 3, "DAA(cs1.0,n3)"),
    (1.0, 4, "DAA(cs1.0,n4)"),
    (0.5, 4, "DAA(cs0.5,n4)_b"),   # rerun for grid symmetry / DSR accounting
    (1.0, 3, "DAA(cs1.0,n3)_b"),
]

rows27 = []
trial_sharpes27 = []
oos_rets27 = {}

for cs, n, label in DAA_GRID:
    w = daa.multi_signals(panel_daa, canary_sensitivity=cs, offensive_n=n)
    m = wf_metrics_multi(panel_daa, w, label)
    r_oos  = m.pop("_r_oos")
    r_full = m.pop("_r_full")
    trial_sharpes27.append(m["oos_sharpe"])
    oos_rets27[label] = r_oos
    rows27.append({**m, "_r_full": r_full})
    print(f"  {m}")

best27 = max(rows27, key=lambda r: r["mean_wf"])
r27_best_full = best27.pop("_r_full")
for r in rows27:
    r.pop("_r_full", None)
best27_label = best27["label"]
r27_best_oos = oos_rets27[best27_label]

print(f"\n  BEST: {best27}")

dsr27, ci27 = significance(r27_best_oos, trial_sharpes27, best27_label, spy_oos_ret)

a27, b27 = r27_best_oos.align(r_v2_oos, join="inner")
corr27 = float(a27.corr(b27))
print(f"  corr(DAA,v2) OOS: {corr27:.3f}")

verdict27_pass = (
    best27["mean_wf"] >= V2_MEAN_WF_SHARPE
    and best27["worst_dd"] > V2_WORST_DD
    and dsr27 >= 0.95
    and ci27.clears_noise
)
watchlist27 = not verdict27_pass and dsr27 >= 0.95 and corr27 < 0.50
verdict27 = "adopted" if verdict27_pass else "discarded"

evidence27 = {
    "best": best27,
    "dsr": round(dsr27, 4),
    "diff_ci": [round(ci27.lo, 3), round(ci27.hi, 3)],
    "corr_v2_oos": round(corr27, 3),
    "all_rows": rows27,
    "watchlist_eligible": watchlist27,
}
record_outcome(reg27.id, verdict=verdict27, evidence=evidence27)
print(f"\nE27 VERDICT: {verdict27} | watch-list: {watchlist27}")

# ---------------------------------------------------------------------------
# 7. v2 full-sample significance re-check
# ---------------------------------------------------------------------------
print("\n=== v2 FULL-SAMPLE CI RE-CHECK ===")
dsr_v2     = ev.deflated_sharpe_ratio(r_v2, [ev.sharpe_ratio(r_v2)])
ci_v2_spy  = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2_spy.lo:.4f},{ci_v2_spy.hi:.4f}]  "
      f"clears={ci_v2_spy.clears_noise}")

# ---------------------------------------------------------------------------
# 8. $1,000 benchmark comparison (all benchmarks requested)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON (2000 → latest) ===")

def end_value(prices, start="2000-01-01"):
    p = prices.loc[start:]
    r = p.pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia  = loader.load_ohlcv("DIA")["Close"];  dia  = dia[dia.index  < HOLDOUT_START]
qqq  = loader.load_ohlcv("QQQ")["Close"];  qqq  = qqq[qqq.index  < HOLDOUT_START]
iwm  = loader.load_ohlcv("IWM")["Close"];  iwm  = iwm[iwm.index  < HOLDOUT_START]
acwi = loader.load_ohlcv("ACWI")["Close"]; acwi = acwi[acwi.index < HOLDOUT_START]
eem  = loader.load_ohlcv("EEM")["Close"];  eem  = eem[eem.index  < HOLDOUT_START]
ewc  = loader.load_ohlcv("EWC")["Close"];  ewc  = ewc[ewc.index  < HOLDOUT_START]

# Mag-7 equal-weight from common start
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
mag7_panel = loader.load_universe(mag7, start="2012-05-18")
mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna()
mag7_ret   = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
mag7_end   = round(float((1 + mag7_ret).prod() * 1000), 2)

v2_end    = round(float((1 + r_v2).prod()       * 1000), 2)
turtle_end= round(float((1 + r26_best_full).prod() * 1000), 2)
daa_end   = round(float((1 + r27_best_full).prod() * 1000), 2)

spy_end  = end_value(spy)
dia_end  = end_value(dia)
qqq_end  = end_value(qqq)
iwm_end  = end_value(iwm)
acwi_end = end_value(acwi, start="2008-03-28")
eem_end  = end_value(eem,  start="2003-04-14")
ewc_end  = end_value(ewc)

print(f"\n  $1,000 from 2000 → {latest_spy_date.date()} (pre-holdout):")
print(f"    v2 champion:      ${v2_end:>10,.2f}")
print(f"    Turtle (E26):     ${turtle_end:>10,.2f}  ({best26_label})")
print(f"    DAA (E27):        ${daa_end:>10,.2f}  ({best27_label})")
print(f"    QQQ (NASDAQ-100): ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):    ${spy_end:>10,.2f}")
print(f"    DIA (DOW):        ${dia_end:>10,.2f}")
print(f"    IWM (Russell 2k): ${iwm_end:>10,.2f}")
print(f"    EWC (Canada):     ${ewc_end:>10,.2f}")
print(f"    EEM (Em. Mkts):   ${eem_end:>10,.2f}  (from 2003)")
print(f"    ACWI (World):     ${acwi_end:>10,.2f}  (from 2008)")
print(f"\n  $1,000 from 2012 (when all Mag-7 listed, survivorship bias):")
print(f"    Mag-7 equal-wt:   ${mag7_end:>10,.2f}")

# ---------------------------------------------------------------------------
# 9. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak   = max(PEAK_VALUE, new_value)
dd_pct     = (new_value / new_peak - 1) * 100

note_s16 = (
    f"Session 16 (2026-07-22): SPY close {latest_spy_close:.4f} ({latest_spy_date.date()}), "
    f"{spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). v2 exposure {current_sig:.4f}. No trades. "
    f"E26 Turtle: {verdict26} (best {best26_label} mean_wf={best26['mean_wf']}, "
    f"DD={best26['worst_dd']}%, DSR={dsr26:.4f}, corr_v2={corr26:.3f}, watch={watchlist26}). "
    f"E27 DAA: {verdict27} (best {best27_label} mean_wf={best27['mean_wf']}, "
    f"DD={best27['worst_dd']}%, DSR={dsr27:.4f}, corr_v2={corr27:.3f}, watch={watchlist27}). "
    f"Guardrails {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN'}."
)

history_entry = {
    "date": "2026-07-22",
    "session": 16,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(port_chg, 2),
    "chg_pct": round(port_pct, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s16,
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
# 10. Summary + save results
# ---------------------------------------------------------------------------
total_configs = trials_this_period()

print(f"\n=== SESSION 16 SUMMARY ===")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f}")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN'}")
print(f"DD from peak: {dd_pct:+.2f}%")
print(f"\nE26 Turtle Trend: {verdict26}")
print(f"  Best: {best26_label}")
print(f"  Mean WF Sharpe: {best26['mean_wf']}  (bar: {V2_MEAN_WF_SHARPE})")
print(f"  Worst DD:       {best26['worst_dd']}%  (bar: {V2_WORST_DD}%)")
print(f"  DSR:            {dsr26:.4f}  (bar: 0.95)")
print(f"  CI:             [{ci26.lo:.3f},{ci26.hi:.3f}]  clears={ci26.clears_noise}")
print(f"  corr(v2):       {corr26:.3f}  watch-list: {watchlist26}")
print(f"\nE27 DAA (Canary): {verdict27}")
print(f"  Best: {best27_label}")
print(f"  Mean WF Sharpe: {best27['mean_wf']}  (bar: {V2_MEAN_WF_SHARPE})")
print(f"  Worst DD:       {best27['worst_dd']}%  (bar: {V2_WORST_DD}%)")
print(f"  DSR:            {dsr27:.4f}  (bar: 0.95)")
print(f"  CI:             [{ci27.lo:.3f},{ci27.hi:.3f}]  clears={ci27.clears_noise}")
print(f"  corr(v2):       {corr27:.3f}  watch-list: {watchlist27}")
print(f"\nTotal configs burned: {total_configs}")

results = {
    "session": "2026-07-22-s16",
    "portfolio_mark": {
        "date": str(latest_spy_date.date()),
        "value": new_value,
        "spy_close": latest_spy_close,
        "spy_day_chg_pct": round(spy_day_chg, 3),
        "port_chg_pct": round(port_pct, 3),
        "all_time_pct": round(all_time_pct, 3),
        "spy_since_live_pct": round(spy_since_live, 3),
        "v2_exposure": round(current_sig, 4),
        "dd_from_peak_pct": round(dd_pct, 2),
    },
    "guardrails": guardrail_result,
    "E26_Turtle": {
        "verdict": verdict26,
        "best": best26,
        "dsr": round(dsr26, 4),
        "ci": [round(ci26.lo, 3), round(ci26.hi, 3)],
        "corr_v2_oos": round(corr26, 3),
        "all_rows": rows26,
        "watchlist_eligible": watchlist26,
    },
    "E27_DAA": {
        "verdict": verdict27,
        "best": best27,
        "dsr": round(dsr27, 4),
        "ci": [round(ci27.lo, 3), round(ci27.hi, 3)],
        "corr_v2_oos": round(corr27, 3),
        "all_rows": rows27,
        "watchlist_eligible": watchlist27,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2_spy.lo, 4), round(ci_v2_spy.hi, 4)],
        "clears": ci_v2_spy.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end,
        "Turtle_best": turtle_end,
        "DAA_best": daa_end,
        "QQQ": qqq_end,
        "SPY": spy_end,
        "DIA": dia_end,
        "IWM": iwm_end,
        "EWC": ewc_end,
        "EEM_from2003": eem_end,
        "ACWI_from2008": acwi_end,
        "Mag7_eqw_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_22.json", "w"), indent=1)
print("\nResults saved → research/results_2026_07_22.json")
