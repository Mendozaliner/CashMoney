"""Session 25 (2026-07-31): Two new investing-philosophy experiments.

Philosophies researched this session:

E38 — Inverse-Volatility GTAA on Swensen-4 Universe
  Philosophy: Risk Parity (Qian 2005; Asness, Frazzini & Pedersen 2012).
  Equal-weight portfolios are dominated by equity vol. Weighting by 1/σ gives
  each asset an equal RISK contribution rather than an equal DOLLAR contribution.
  Universe: SPY / IEF / GLD / VNQ (Swensen-4 from E37), inverse-vol weights,
  each independently SMA-gated.
  Distinction from E12 Risk Parity (3-asset SPY/IEF/GLD):
    Adds VNQ (real estate). ROADMAP s24 explicitly suggests this test.
  Distinction from E37 Swensen-4 (equal 25% weights):
    Same universe; risk-weighted rather than dollar-weighted.

E39 — Real Earnings Growth Filter (Shiller Macro Overlay)
  Philosophy: Earnings momentum as a macro quality filter (Novy-Marx 2013;
  Chan, Jegadeesh & Lakonishok 1996). When real (CPI-adjusted) Shiller
  earnings are contracting on a 12-month basis, equity risk is elevated.
  Distinction from E31 CAPE Tilt (CAPE LEVEL → always top decile OOS):
    This uses the DIRECTION and RATE OF CHANGE of real earnings, which
    varies meaningfully in all periods including the 2020-2025H OOS window
    (real earnings fell ~8% in H2-2022; recovered in 2023-24).
  Distinction from E32 Yield Curve (CLOSED):
    Earnings growth is a fundamental economic signal, not a rate/duration signal.

Data through: checked at runtime.
Champion configs entering session: 245.
"""
import sys
import json
import pathlib
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, multi_engine as me
from backtest import evaluation as ev, guardrails as gr
from backtest import live_track
from strategies import vol_target
from strategies import inv_vol_gtaa, earnings_growth
from research.preregister import preregister, record_outcome, trials_this_period

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
for k, v in fresh.items():
    print(f"  {k}: {v}")

stale = int(fresh.get("stale_days", 0) or 0)

spy_full  = loader.load_ohlcv("SPY")
spy_all   = spy_full["Close"]
spy       = spy_full[spy_full.index < HOLDOUT_START]["Close"]

ief_full  = loader.load_ohlcv("IEF")["Close"]
gld_full  = loader.load_ohlcv("GLD")["Close"]
vnq_full  = loader.load_ohlcv("VNQ")["Close"]
dia_full  = loader.load_ohlcv("DIA")["Close"]
qqq_full  = loader.load_ohlcv("QQQ")["Close"]
iwm_full  = loader.load_ohlcv("IWM")["Close"]

irx_full  = loader.load_ohlcv("^IRX")["Close"].reindex(spy_all.index).ffill()
rf_daily  = (irx_full / 100.0) / 252.0

spy_ret     = spy.pct_change().fillna(0.0)
spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

latest_spy_date  = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close   = float(spy_all.iloc[-2])

print(f"\nData through {latest_spy_date.date()}, SPY={latest_spy_close:.4f}")
print(f"Configs entering this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + v2 signal + guardrails
# ---------------------------------------------------------------------------
UNITS       = 1.3334757435413753
PREV_VALUE  = 987.92        # last confirmed mark (s24, 2026-07-28 close)
PEAK_VALUE  = 1006.52
INCEPTION   = 1000.0
LIVE_SPY_BASE = 749.1699829101562

new_value    = round(UNITS * latest_spy_close, 2)
spy_day_chg  = (latest_spy_close / prev_spy_close - 1) * 100
port_chg     = new_value - PREV_VALUE
port_pct     = (new_value / PREV_VALUE - 1) * 100
all_time_pct = (new_value / INCEPTION - 1) * 100
spy_since_live = (latest_spy_close / LIVE_SPY_BASE - 1) * 100

print(f"\n=== PORTFOLIO MARK ({latest_spy_date.date()}) ===")
print(f"  SPY close: {latest_spy_close:.4f}  (day: {spy_day_chg:+.3f}%)")
print(f"  Value: ${new_value:.2f}  ({port_chg:+.2f}, {port_pct:+.3f}%)")
print(f"  All-time: {all_time_pct:+.3f}%  |  SPY since live: {spy_since_live:+.3f}%")
print(f"  Peak: ${PEAK_VALUE:.2f}")

portfolio_json_path = pathlib.Path("portfolio.json")
with open(portfolio_json_path) as f:
    portfolio = json.load(f)

sma200      = spy_all.rolling(200).mean().iloc[-1]
band_up     = sma200 * 1.03
band_dn     = sma200 * 0.97
vol20       = spy_all.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
current_sig = float(vol_target.signals(spy_all, target_vol=0.18, lookback=20).iloc[-1])
trend_state = "ON" if latest_spy_close > band_up else (
    "OFF" if latest_spy_close < band_dn else "HOLD")

print(f"\n=== V2 SIGNAL ===")
print(f"  SMA200={sma200:.2f}  band_up={band_up:.2f}  close={latest_spy_close:.2f}  "
      f"trend={trend_state}")
print(f"  20d vol={vol20*100:.1f}%  scale={min(1.0, 0.18/vol20):.4f}")
print(f"  v2 exposure: {current_sig:.4f}")

guardrail_result = gr.run_all(
    portfolio, spy_returns=spy_ret, stale_days=stale, peak_value=PEAK_VALUE
)
print(f"\n=== GUARDRAILS ===")
for c in guardrail_result["checks"]:
    status = "GREEN" if c["ok"] else "!! NON-GREEN !!"
    print(f"  {c['guardrail']}: {status}  {c.get('detail','')}{c.get('level','')}")

# ---------------------------------------------------------------------------
# 3. Live track (Phase-2 graduation checkpoint)
# ---------------------------------------------------------------------------
print(f"\n=== LIVE TRACK (Phase-2 Graduation) ===")
try:
    lt_summary = live_track.summary(portfolio, spy_all)
    for k, v in lt_summary.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"  (live_track.summary error: {e})")

# ---------------------------------------------------------------------------
# 4. Walk-forward helpers
# ---------------------------------------------------------------------------
def wf_single(series: pd.Series, label: str) -> dict:
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        x = series.loc[a:b]
        if len(x) < 60:
            fold_sharpes.append(0.0)
            continue
        fold_sharpes.append(round(float(ev.sharpe_ratio(x)), 3))
        eq = (1 + x).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    oos  = series.loc[OOS_A:OOS_B]
    full = (1 + series).prod()
    return {
        "label": label,
        "folds": fold_sharpes,
        "mean_wf": round(float(np.mean(fold_sharpes)), 3),
        "worst_dd": round(worst_dd * 100, 2),
        "oos_sharpe": round(float(ev.sharpe_ratio(oos)), 3),
        "end1k": round(float(full * 1000), 2),
    }


def wf_multi(price_panel_full: pd.DataFrame, weights_full: pd.DataFrame,
             label: str) -> dict:
    fold_sharpes, worst_dd = [], 0.0
    _rf = rf_daily
    for name, a, b in FOLDS:
        pan_f = price_panel_full.loc[a:b]
        wgt_f = weights_full.loc[a:b]
        if len(pan_f) < 60:
            fold_sharpes.append(0.0)
            continue
        r = me.portfolio_returns(pan_f, wgt_f, commission=COST,
                                 rf_daily=_rf.reindex(pan_f.index).fillna(0))
        fold_sharpes.append(round(float(ev.sharpe_ratio(r)), 3))
        eq = (1 + r).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    r_oos = me.portfolio_returns(
        price_panel_full.loc[OOS_A:OOS_B],
        weights_full.loc[OOS_A:OOS_B],
        commission=COST,
        rf_daily=_rf.reindex(price_panel_full.loc[OOS_A:OOS_B].index).fillna(0),
    )
    r_full = me.portfolio_returns(price_panel_full, weights_full,
                                  commission=COST,
                                  rf_daily=_rf.reindex(price_panel_full.index).fillna(0))
    full_val = float((1 + r_full).prod() * 1000)
    return {
        "label": label,
        "folds": fold_sharpes,
        "mean_wf": round(float(np.mean(fold_sharpes)), 3),
        "worst_dd": round(worst_dd * 100, 2),
        "oos_sharpe": round(float(ev.sharpe_ratio(r_oos)), 3),
        "end1k": round(full_val, 2),
        "_r_oos": r_oos,
        "_r_full": r_full,
    }


def significance(r_oos, trial_sharpes, label):
    dsr = ev.deflated_sharpe_ratio(r_oos, trial_sharpes)
    ci  = ev.bootstrap_difference_ci(r_oos, spy_oos_ret)
    print(f"    {label}: DSR={dsr:.4f}  CI=[{ci.lo:.3f},{ci.hi:.3f}]  "
          f"clears={ci.clears_noise}")
    return float(dsr), ci

# ---------------------------------------------------------------------------
# 5. Baselines
# ---------------------------------------------------------------------------
sig_v2   = vol_target.signals(spy, target_vol=0.18, lookback=20)
r_v2     = ve.strategy_returns(spy, sig_v2, commission=COST,
                               rf_daily=rf_daily.reindex(spy.index).fillna(0))
r_v2_oos = r_v2.loc[OOS_A:OOS_B]

bm_v2  = wf_single(r_v2, "v2 champion")
bm_spy = wf_single(spy_ret, "SPY B&H")

print("\n=== BASELINES ===")
print(f"  v2 champion: folds={bm_v2['folds']}  mean_wf={bm_v2['mean_wf']}  "
      f"worst_dd={bm_v2['worst_dd']}%  end1k=${bm_v2['end1k']:,.2f}")
print(f"  SPY B&H:     folds={bm_spy['folds']}  mean_wf={bm_spy['mean_wf']}  "
      f"worst_dd={bm_spy['worst_dd']}%  end1k=${bm_spy['end1k']:,.2f}")

# Price panel for multi-asset (E38)
def _align(s):
    return s.reindex(spy.index).ffill()

panel_sw4 = pd.DataFrame({
    "SPY": spy,
    "IEF": _align(ief_full),
    "GLD": _align(gld_full),
    "VNQ": _align(vnq_full),
}).dropna(how="all")

# ---------------------------------------------------------------------------
# 6. ROADMAP #10: v2 full-sample significance re-check
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2 = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2  = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s24: CI=[-0.0128,+0.7077])")

# ---------------------------------------------------------------------------
# 7. E38: Inverse-Vol GTAA on Swensen-4 Universe
# ---------------------------------------------------------------------------
print("\n=== E38: INVERSE-VOL GTAA (Swensen-4 Universe) ===")

reg38 = preregister(
    hypothesis=(
        "Risk-parity theory (Qian 2005; Asness, Frazzini & Pedersen 2012): "
        "weighting by inverse realized volatility gives each asset class a more "
        "equal RISK contribution than equal dollar weighting. Applied to the "
        "Swensen-4 universe (SPY/IEF/GLD/VNQ) with per-asset SMA trend gates. "
        "Motivation: E37 (Swensen-4, equal weights) was DISCARDED with "
        "mean_wf=0.748 because equal weights allocated the same DOLLARS to "
        "high-vol (SPY, VNQ) and low-vol (IEF, GLD) assets, creating equity "
        "dominance. Inverse-vol weighting naturally overweights IEF and GLD "
        "(low vol) relative to SPY and VNQ (high vol), which should provide "
        "better risk-adjusted balance and lower drawdowns. ROADMAP s24 explicitly "
        "states: 'inverse-vol weighting on the Swensen universe (similar to E12 "
        "risk parity) might preserve the DD benefit.' "
        "Distinction from E12 Risk Parity (SPY/IEF/GLD): adds VNQ as a 4th "
        "asset, testing whether real estate improves risk-parity diversification. "
        "Skeptical prior: (a) IEF dominated inverse-vol in 2022 when bond returns "
        "were severely negative, just like E12 failed; (b) VNQ may be too "
        "correlated with SPY to add meaningful diversification at the ETF level; "
        "(c) with 245+ prior configs, DSR penalty is severe."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 245 + 4 new configs = 249 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Watch-list: DSR >= 0.95 AND OOS corr to v2 < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

E38_GRID = [
    dict(vol_lookback=60,  sma_window=150, label="IVG(vl60,sma150)"),
    dict(vol_lookback=60,  sma_window=200, label="IVG(vl60,sma200)"),
    dict(vol_lookback=252, sma_window=150, label="IVG(vl252,sma150)"),
    dict(vol_lookback=252, sma_window=200, label="IVG(vl252,sma200)"),
]

rows38, trial_sh38, oos38, full38 = [], [], {}, {}
for cfg in E38_GRID:
    lbl = cfg.pop("label")
    try:
        wts = inv_vol_gtaa.multi_signals(
            spy,
            ief=_align(ief_full),
            gld=_align(gld_full),
            vnq=_align(vnq_full),
            **cfg,
        )
        panel_c = panel_sw4.reindex(columns=wts.columns)
        m = wf_multi(panel_c, wts, lbl)
        trial_sh38.append(m["oos_sharpe"])
        oos38[lbl] = m.pop("_r_oos")
        full38[lbl] = m.pop("_r_full")
        rows38.append({**m, "label": lbl})
        print(f"  {m}")
    except Exception as e:
        import traceback
        print(f"  ERROR on {lbl}: {e}")
        traceback.print_exc()

if not rows38:
    print("  All E38 configs failed.")
    verdict38 = "inconclusive"
    best38 = {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr38, ci38, corr38, watch38 = 0.0, None, 1.0, False
else:
    best38 = max(rows38, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E38: {best38}")
    dsr38, ci38 = significance(oos38[best38["label"]], trial_sh38, best38["label"])
    corr38 = float(oos38[best38["label"]].corr(r_v2_oos))
    print(f"  corr(IVG,v2) OOS: {corr38:.3f}")

    pass38 = (best38["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best38["worst_dd"] > V2_WORST_DD and
              dsr38 >= 0.95 and ci38.clears_noise)
    watch38 = not pass38 and dsr38 >= 0.95 and corr38 < 0.50
    verdict38 = "adopted" if pass38 else "discarded"

    ev38 = {"best": best38, "dsr": round(dsr38, 4),
            "diff_ci": [round(ci38.lo, 3), round(ci38.hi, 3)],
            "corr_v2_oos": round(corr38, 3), "all_rows": rows38,
            "watchlist_eligible": watch38}
    record_outcome(reg38.id, verdict=verdict38, evidence=ev38)
    print(f"\n  E38 VERDICT: {verdict38} | watch-list eligible: {watch38}")

# ---------------------------------------------------------------------------
# 8. E39: Real Earnings Growth Filter (Shiller Macro Overlay)
# ---------------------------------------------------------------------------
print("\n=== E39: REAL EARNINGS GROWTH FILTER (Shiller Macro Overlay) ===")

# Verify Shiller data is available
try:
    sh = loader.load_shiller()
    print(f"  Shiller data available: {sh.index[0].date()} → {sh.index[-1].date()}, "
          f"rows={len(sh)}, cols={list(sh.columns)}")
    shiller_ok = True
except Exception as e:
    print(f"  Shiller data NOT available: {e}")
    shiller_ok = False

reg39 = preregister(
    hypothesis=(
        "Real Shiller earnings growth (12-month change in CPI-adjusted Shiller "
        "earnings) as a macro quality filter overlaid on v2. Hypothesis: when "
        "real earnings are CONTRACTING (growth_12m < threshold), the economic "
        "backdrop is deteriorating and equity downside risk is elevated; reducing "
        "v2 exposure during these periods improves risk-adjusted returns. "
        "Key distinction from E31 CAPE Tilt (DISCARDED, s22): E31 used CAPE LEVEL "
        "(always in the top decile OOS, corr_v2=1.000). This uses earnings MOMENTUM "
        "(direction and rate of change), which varied meaningfully during 2020-2025H: "
        "real earnings fell ~8% in H2-2022 (earnings recession) but recovered in 2023-24. "
        "The signal turns on and off at fundamental inflection points, not based on a "
        "static valuation level. "
        "Key distinction from E32 Yield Curve (CLOSED): earnings growth is a "
        "real-economy signal derived from corporate fundamentals, not from the "
        "interest rate structure. "
        "Skeptical prior: (a) SPY SMA200 gate may already capture earnings recessions "
        "via price action; (b) monthly Shiller earnings data is backward-looking and "
        "may lag price signals; (c) DSR penalty at 249+ configs is severe."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 249 + 4 new configs = 253 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Watch-list: DSR >= 0.95 AND OOS corr to v2 < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

E39_GRID = [
    dict(growth_threshold=-0.05, de_risk_scale=0.50,
         label="EG(thr-5%,sc0.50)"),
    dict(growth_threshold=-0.05, de_risk_scale=0.75,
         label="EG(thr-5%,sc0.75)"),
    dict(growth_threshold=-0.10, de_risk_scale=0.50,
         label="EG(thr-10%,sc0.50)"),
    dict(growth_threshold=-0.10, de_risk_scale=0.75,
         label="EG(thr-10%,sc0.75)"),
]

rows39, trial_sh39, oos39, full39 = [], [], {}, {}
for cfg in E39_GRID:
    lbl = cfg.pop("label")
    try:
        sig = earnings_growth.signals(spy, **cfg)
        r = ve.strategy_returns(spy, sig, commission=COST,
                                rf_daily=rf_daily.reindex(spy.index).fillna(0))
        m = wf_single(r, lbl)
        trial_sh39.append(m["oos_sharpe"])
        oos39[lbl] = r.loc[OOS_A:OOS_B]
        full39[lbl] = r
        rows39.append(m)
        print(f"  {m}")
    except Exception as e:
        import traceback
        print(f"  ERROR on {lbl}: {e}")
        traceback.print_exc()

if not rows39:
    print("  All E39 configs failed.")
    verdict39 = "inconclusive"
    best39 = {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr39, ci39, corr39, watch39 = 0.0, None, 1.0, False
else:
    best39 = max(rows39, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E39: {best39}")
    dsr39, ci39 = significance(oos39[best39["label"]], trial_sh39, best39["label"])
    corr39 = float(oos39[best39["label"]].corr(r_v2_oos))
    print(f"  corr(EG,v2) OOS: {corr39:.3f}")

    pass39 = (best39["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best39["worst_dd"] > V2_WORST_DD and
              dsr39 >= 0.95 and ci39.clears_noise)
    watch39 = not pass39 and dsr39 >= 0.95 and corr39 < 0.50
    verdict39 = "adopted" if pass39 else "discarded"

    ev39 = {"best": best39, "dsr": round(dsr39, 4),
            "diff_ci": [round(ci39.lo, 3), round(ci39.hi, 3)],
            "corr_v2_oos": round(corr39, 3), "all_rows": rows39,
            "watchlist_eligible": watch39}
    record_outcome(reg39.id, verdict=verdict39, evidence=ev39)
    print(f"\n  E39 VERDICT: {verdict39} | watch-list eligible: {watch39}")

# ---------------------------------------------------------------------------
# 9. $1,000 benchmark comparison (2000 → latest, pre-holdout)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON (2000 → pre-holdout) ===")

def end_value_from_returns(r: pd.Series) -> float:
    return round(float((1 + r).prod() * 1000), 2)

def end_value_from_prices(prices: pd.Series) -> float:
    r = prices.pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

v2_end   = end_value_from_returns(r_v2)
spy_end  = end_value_from_prices(spy)
dia_end  = end_value_from_prices(dia_full[dia_full.index < HOLDOUT_START])
qqq_end  = end_value_from_prices(qqq_full[qqq_full.index < HOLDOUT_START])
iwm_end  = end_value_from_prices(iwm_full[iwm_full.index < HOLDOUT_START])

e38_end = None
e39_end = None
if rows38 and best38.get("label", "FAILED") != "FAILED":
    _k = best38["label"]
    if _k in full38:
        e38_end = end_value_from_returns(full38[_k])
if rows39 and best39.get("label", "FAILED") != "FAILED":
    _k = best39["label"]
    if _k in full39:
        e39_end = end_value_from_returns(full39[_k])

# International benchmarks
intl = {}
for t in ["EWC", "ACWI", "EFA"]:
    try:
        p = loader.load_ohlcv(t)["Close"]
        p = p[p.index < HOLDOUT_START]
        intl[t] = end_value_from_prices(p)
    except Exception:
        intl[t] = None

# Mag-7 (survivorship-biased, from 2012)
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
try:
    mag7_panel = loader.load_universe(mag7, start="2012-05-18")
    mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna()
    mag7_ret   = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
    mag7_end   = round(float((1 + mag7_ret).prod() * 1000), 2)
except Exception:
    mag7_end = None

print(f"  $1k from 2000 → {latest_spy_date.date()} (pre-holdout {HOLDOUT_START}):")
print(f"    v2 champion:           ${v2_end:>10,.2f}   ← champion")
if e38_end:
    print(f"    E38 Inv-Vol GTAA:      ${e38_end:>10,.2f}   ({best38['label']})")
if e39_end:
    print(f"    E39 Earnings Growth:   ${e39_end:>10,.2f}   ({best39['label']})")
print(f"    QQQ (Nasdaq 100):      ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):         ${spy_end:>10,.2f}")
print(f"    DIA (DOW Jones):       ${dia_end:>10,.2f}")
print(f"    IWM (Russell 2000):    ${iwm_end:>10,.2f}")
if intl.get("EWC"):
    print(f"    EWC (Canada):          {str(intl['EWC']):>11}")
if intl.get("EFA"):
    print(f"    EFA (Intl Devlpd):     {str(intl['EFA']):>11}")
if intl.get("ACWI"):
    print(f"    ACWI (World):          {str(intl['ACWI']):>11}")
if mag7_end:
    print(f"    Mag-7 eqw 2012:        ${mag7_end:>10,.2f}   (surv. bias; G4 cap)")

# ---------------------------------------------------------------------------
# 10. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak     = max(PEAK_VALUE, new_value)
dd_from_peak = (new_value / new_peak - 1) * 100

e38_lbl  = best38.get("label", "N/A") if rows38 else "N/A"
e39_lbl  = best39.get("label", "N/A") if rows39 else "N/A"
ci38_str = f"[{ci38.lo:.3f},{ci38.hi:.3f}]" if ci38 else "N/A"
ci39_str = f"[{ci39.lo:.3f},{ci39.hi:.3f}]" if ci39 else "N/A"

note_s25 = (
    f"Session 25 (2026-07-31): SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f}. No trades. "
    f"E38 Inv-Vol GTAA: {verdict38} (best {e38_lbl} mean_wf={best38['mean_wf']}, "
    f"DD={best38['worst_dd']}%, DSR={dsr38:.4f}, CI={ci38_str}, "
    f"corr_v2={corr38:.3f}, watchlist={watch38}). "
    f"E39 Earnings Growth: {verdict39} (best {e39_lbl} mean_wf={best39['mean_wf']}, "
    f"DD={best39['worst_dd']}%, DSR={dsr39:.4f}, CI={ci39_str}, "
    f"corr_v2={corr39:.3f}, watchlist={watch39}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN'}. "
    f"DD from peak: {dd_from_peak:+.2f}%. $1k v2={v2_end} SPY={spy_end}."
)

history_entry = {
    "date": "2026-07-31",
    "session": 25,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(new_value - PREV_VALUE, 2),
    "chg_pct": round((new_value / PREV_VALUE - 1) * 100, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s25,
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
# 11. Session summary
# ---------------------------------------------------------------------------
total_configs = trials_this_period()
print(f"\n{'='*65}")
print(f"SESSION 25 SUMMARY (2026-07-31)")
print(f"{'='*65}")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% since last mark | "
      f"{all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f} | DD from peak: {dd_from_peak:+.2f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")

print(f"\nv2 significance: DSR={dsr_v2:.4f} | "
      f"CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}] | clears={ci_v2.clears_noise}")

print(f"\nExperiment Results:")
exps = [
    ("E38 Inv-Vol GTAA",     best38, verdict38, dsr38, ci38, watch38, corr38),
    ("E39 Earnings Growth",  best39, verdict39, dsr39, ci39, watch39, corr39),
]
for exp, best, verdict, dsr, ci, watch, corr in exps:
    if ci is None:
        print(f"  {exp}: {verdict.upper()} (no CI computed)")
        continue
    print(f"  {exp}: {verdict.upper()}")
    print(f"    mean_wf={best['mean_wf']} (bar 0.844) | "
          f"DD={best['worst_dd']}% (bar -20.5%) | "
          f"DSR={dsr:.4f} (bar 0.95)")
    print(f"    CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise} | "
          f"corr_v2={corr:.3f} | watchlist={watch}")

print(f"\nChampion v2 UNCHANGED. Total configs: {total_configs}")

results = {
    "session": "2026-07-31-s25",
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
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2.lo, 4), round(ci_v2.hi, 4)],
        "clears": ci_v2.clears_noise,
    },
    "E38_IVG": {
        "verdict": verdict38, "best": best38,
        "dsr": round(dsr38, 4),
        "ci": [round(ci38.lo, 3), round(ci38.hi, 3)] if ci38 else None,
        "corr_v2_oos": round(corr38, 3), "all_rows": rows38,
        "watchlist_eligible": watch38,
    },
    "E39_EG": {
        "verdict": verdict39, "best": best39,
        "dsr": round(dsr39, 4),
        "ci": [round(ci39.lo, 3), round(ci39.hi, 3)] if ci39 else None,
        "corr_v2_oos": round(corr39, 3), "all_rows": rows39,
        "watchlist_eligible": watch39,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E38_IVG": e38_end, "E39_EG": e39_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end, "IWM": iwm_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"), "ACWI": intl.get("ACWI"),
        "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_31.json", "w"), indent=1)
print("Results saved → research/results_2026_07_31.json")
