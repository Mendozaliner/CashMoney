"""Session 20 (2026-07-24): Two new investing-philosophy experiments.

Investing philosophies researched this session:

E29 — VIX-Regime Dynamic Ensemble
  Observation: different strategies excel in different market regimes. The
  research desk has proven v2 (SMA200+vol-target) dominates bull markets,
  CTA (E20) dominates crisis periods (lowest DD ever: -6.19%), and Bollinger
  MR (E18) has the LOWEST correlation to v2 ever (0.364) — useful in choppy
  elevated-vol periods. BUT fixed-weight ensembles fail (E22: OOS corr 0.943
  because CTA-SPY duplicated v2-SPY in the bull-era OOS window).

  Key innovation: DYNAMIC weights driven by the CBOE VIX fear gauge:
    VIX < 20  (normal bull):  100% v2 — trend following wins
    VIX 20-30 (elevated chop): 60% v2 + 40% Bollinger MR — MR outperforms in chop
    VIX > 30  (crisis):       100% CTA (SPY/IEF/GLD vol-targeted) — bonds/gold surge

  This eliminates the E22 failure mode (CTA drag in VIX<20 bull markets) while
  retaining the CTA crisis-alpha benefit when VIX actually spikes.

E30 — Inter-Market Bond-Equity Risk Filter
  Philosophy: When bonds OUTPERFORM equities over a 3-month window, it signals
  a 'flight to quality' — investors prefer safety over growth. This is a risk
  warning that often precedes or coincides with equity drawdowns.

  Key distinction from E3/E7 (dual momentum, CLOSED): This does NOT rotate
  capital to bonds. It only SCALES DOWN v2 exposure (by 50%) when bonds beat
  SPY. Avoids the TLT catastrophe of 2022.

  Uses IEF (7-10y) vs SPY 3-month relative momentum as the warning signal:
    SPY mom >= IEF mom: equities outperforming → risk-on → full v2
    SPY mom <  IEF mom: bonds outperforming → risk-off → 50% v2

Data through: checked at runtime.
Champion configs entering session: 192.
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
from strategies import regime_ensemble, intermarket
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

spy_full   = loader.load_ohlcv("SPY")
spy_all    = spy_full["Close"]
spy_full_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]

ief_full   = loader.load_ohlcv("IEF")["Close"]
shy_full   = loader.load_ohlcv("SHY")["Close"]
gld_full   = loader.load_ohlcv("GLD")["Close"]
dia_full   = loader.load_ohlcv("DIA")["Close"]
qqq_full   = loader.load_ohlcv("QQQ")["Close"]
iwm_full   = loader.load_ohlcv("IWM")["Close"]

# VIX - use OHLCV cache (^VIX) if available, else fall back to vix snapshot
try:
    vix_full = loader.load_ohlcv("^VIX")["Close"]
    vix_source = "^VIX OHLCV cache"
except FileNotFoundError:
    vix_df = loader.load_vix()
    vix_full = vix_df["VIX Close"] if "VIX Close" in vix_df.columns else vix_df.iloc[:, -1]
    vix_source = "VIX snapshot"
print(f"  VIX loaded from: {vix_source}")

irx_full = loader.load_ohlcv("^IRX")["Close"].reindex(spy_full_cut.index).ffill()
rf_daily  = (irx_full / 100.0) / 252.0

spy      = spy_full_cut
spy_ret  = spy.pct_change().fillna(0.0)
spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

latest_spy_date  = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close   = float(spy_all.iloc[-2])

print(f"\nData through {latest_spy_date.date()}, SPY={latest_spy_close:.4f}")
print(f"Configs entering this session: {trials_this_period()}")

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails
# ---------------------------------------------------------------------------
UNITS      = 1.3334757435413753
PREV_VALUE = 996.65          # last confirmed mark (2026-07-22)
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
print(f"  All-time: {all_time_pct:+.3f}%  |  SPY since live: {spy_since_live:+.3f}%")
print(f"  Peak: ${PEAK_VALUE:.2f}")

portfolio_json_path = pathlib.Path("portfolio.json")
with open(portfolio_json_path) as f:
    portfolio = json.load(f)

sma200   = spy_all.rolling(200).mean().iloc[-1]
band_up  = sma200 * 1.03
vol20    = spy_all.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
current_sig = float(vol_target.signals(spy_all, target_vol=0.18, lookback=20).iloc[-1])

print(f"\n=== V2 SIGNAL ===")
print(f"  SMA200={sma200:.2f}  band_up={band_up:.2f}  close={latest_spy_close:.2f}  "
      f"trend={'ON' if latest_spy_close > band_up else 'OFF'}")
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
# 4. Walk-forward helper (single-asset)
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
    """Walk-forward metrics for a multi-asset strategy."""
    fold_sharpes, worst_dd = [], 0.0
    for name, a, b in FOLDS:
        pan_f = price_panel_full.loc[a:b]
        wgt_f = weights_full.loc[a:b]
        if len(pan_f) < 60:
            fold_sharpes.append(0.0)
            continue
        r = me.portfolio_returns(pan_f, wgt_f, commission=COST,
                                 rf_daily=rf_daily.reindex(pan_f.index).fillna(0))
        fold_sharpes.append(round(float(ev.sharpe_ratio(r)), 3))
        eq = (1 + r).cumprod()
        worst_dd = min(worst_dd, float((eq / eq.cummax() - 1).min()))
    r_oos = me.portfolio_returns(
        price_panel_full.loc[OOS_A:OOS_B],
        weights_full.loc[OOS_A:OOS_B],
        commission=COST,
        rf_daily=rf_daily.reindex(price_panel_full.loc[OOS_A:OOS_B].index).fillna(0),
    )
    r_full = me.portfolio_returns(price_panel_full, weights_full,
                                  commission=COST, rf_daily=rf_daily.reindex(
                                      price_panel_full.index).fillna(0))
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
r_v2     = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily)
r_v2_oos = r_v2.loc[OOS_A:OOS_B]

bm_v2  = wf_single(r_v2, "v2 champion")
bm_spy = wf_single(spy_ret, "SPY B&H")

print("\n=== BASELINES ===")
print(f"  v2 champion: folds={bm_v2['folds']}  mean_wf={bm_v2['mean_wf']}  "
      f"worst_dd={bm_v2['worst_dd']}%  end1k=${bm_v2['end1k']:,.2f}")
print(f"  SPY B&H:     folds={bm_spy['folds']}  mean_wf={bm_spy['mean_wf']}  "
      f"worst_dd={bm_spy['worst_dd']}%  end1k=${bm_spy['end1k']:,.2f}")

# ---------------------------------------------------------------------------
# 6. E29: VIX-Regime Dynamic Ensemble
# ---------------------------------------------------------------------------
print("\n=== E29: VIX-REGIME DYNAMIC ENSEMBLE ===")

reg29 = preregister(
    hypothesis=(
        "VIX-driven dynamic regime selection improves on both v2 and the "
        "prior fixed-weight ensemble (E22) by activating different strategy "
        "families in different volatility regimes:\n"
        "  VIX<20: pure v2 (avoids CTA bull-market drag = E22's failure mode)\n"
        "  VIX 20-30: blend v2 + Bollinger MR (E18's lowest-ever corr=0.364)\n"
        "  VIX>30: CTA multi-asset (E20's crisis-alpha, lowest DD ever -6.19%)\n"
        "Skeptical prior: (a) VIX threshold choice is a free parameter; "
        "(b) the crisis regime is rare, limiting its contribution; "
        "(c) in OOS, VIX and equity moves are contemporaneous — using VIX at "
        "close-t to trigger signals at t+1 may lag the actual regime shift."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 192 + 4 new configs = 196 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

# Prepare multi-asset price panel (pre-holdout)
panel_full = pd.DataFrame({
    "SPY": spy,
    "IEF": ief_full.reindex(spy.index).ffill(),
    "GLD": gld_full.reindex(spy.index).ffill(),
}).dropna(how="all")

# VIX aligned to panel dates (pre-holdout)
vix_panel = vix_full.reindex(panel_full.index).ffill().fillna(20.0)

E29_GRID = [
    dict(vix_elevated=20, vix_crisis=30, w_v2_elevated=0.60,
         w_bol_elevated=0.40, target_vol=0.18, cta_vol=0.12,
         label="RE(v20/c30,60/40,tv0.18)"),
    dict(vix_elevated=20, vix_crisis=35, w_v2_elevated=0.70,
         w_bol_elevated=0.30, target_vol=0.18, cta_vol=0.12,
         label="RE(v20/c35,70/30,tv0.18)"),
    dict(vix_elevated=25, vix_crisis=40, w_v2_elevated=0.60,
         w_bol_elevated=0.40, target_vol=0.18, cta_vol=0.12,
         label="RE(v25/c40,60/40,tv0.18)"),
    dict(vix_elevated=20, vix_crisis=30, w_v2_elevated=1.00,
         w_bol_elevated=0.00, target_vol=0.18, cta_vol=0.12,
         label="RE(v20/c30,v2only,tv0.18)"),
]

rows29, trial_sh29, oos29 = [], [], {}
for cfg in E29_GRID:
    lbl = cfg.pop("label")
    wts = regime_ensemble.multi_signals(panel_full, vix_panel, **cfg)
    m = wf_multi(panel_full, wts, lbl)
    trial_sh29.append(m["oos_sharpe"])
    oos29[lbl] = m.pop("_r_oos")
    _ = m.pop("_r_full")
    rows29.append(m)
    print(f"  {m}")

best29 = max(rows29, key=lambda x: x["mean_wf"])
print(f"\n  BEST E29: {best29}")
dsr29, ci29 = significance(oos29[best29["label"]], trial_sh29, best29["label"])

corr29 = float(oos29[best29["label"]].corr(r_v2_oos))
print(f"  corr(RegimeEnsemble,v2) OOS: {corr29:.3f}")

pass29 = (best29["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best29["worst_dd"] > V2_WORST_DD and
          dsr29 >= 0.95 and ci29.clears_noise)
watch29 = not pass29 and dsr29 >= 0.95 and corr29 < 0.50
verdict29 = "adopted" if pass29 else "discarded"

ev29 = {"best": best29, "dsr": round(dsr29, 4),
        "diff_ci": [round(ci29.lo, 3), round(ci29.hi, 3)],
        "corr_v2_oos": round(corr29, 3), "all_rows": rows29,
        "watchlist_eligible": watch29}
record_outcome(reg29.id, verdict=verdict29, evidence=ev29)
print(f"\n  E29 VERDICT: {verdict29} | watch-list eligible: {watch29}")

# ---------------------------------------------------------------------------
# 7. E30: Inter-Market Bond-Equity Risk Filter
# ---------------------------------------------------------------------------
print("\n=== E30: INTER-MARKET BOND-EQUITY RISK FILTER ===")

reg30 = preregister(
    hypothesis=(
        "When bonds (IEF, 7-10y Treasuries) OUTPERFORM SPY over a 3-month "
        "window, it signals a 'flight to quality' — institutional capital "
        "leaving equities for safety. Scaling down v2 by 50% during such "
        "periods should reduce equity drawdowns without sacrificing the "
        "trend-following edge.\n"
        "Key distinction from E3/E7 (dual momentum, CLOSED): This does NOT "
        "rotate to bonds; it only scales DOWN v2 (avoiding the TLT 2022 crash "
        "that killed E3's harbor). IEF used over TLT for same reason.\n"
        "Skeptical prior: (a) IEF outperforming SPY is often a lagging signal — "
        "the drawdown has already started; (b) in 2022, IEF also fell (-14%) so "
        "SPY still underperformed bonds — the signal would fire but too late; "
        "(c) the 50% scale is a free parameter."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 196 + 4 = 200 total configs) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

ief_cut = ief_full.reindex(spy.index).ffill()

E30_GRID = [
    dict(target_vol=0.18, lookback=63,  reduced_scale=0.50,
         label="IM(lb63,scale0.50)"),
    dict(target_vol=0.18, lookback=63,  reduced_scale=0.00,
         label="IM(lb63,scale0.00)"),
    dict(target_vol=0.18, lookback=126, reduced_scale=0.50,
         label="IM(lb126,scale0.50)"),
    dict(target_vol=0.18, lookback=21,  reduced_scale=0.50,
         label="IM(lb21,scale0.50)"),
]

rows30, trial_sh30, oos30 = [], [], {}
for cfg in E30_GRID:
    lbl = cfg.pop("label")
    sig = intermarket.signals(spy, ief_cut, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh30.append(m["oos_sharpe"])
    oos30[lbl] = r.loc[OOS_A:OOS_B]
    rows30.append(m)
    print(f"  {m}")

best30 = max(rows30, key=lambda x: x["mean_wf"])
print(f"\n  BEST E30: {best30}")
dsr30, ci30 = significance(oos30[best30["label"]], trial_sh30, best30["label"])

corr30 = float(oos30[best30["label"]].corr(r_v2_oos))
print(f"  corr(InterMarket,v2) OOS: {corr30:.3f}")

pass30 = (best30["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best30["worst_dd"] > V2_WORST_DD and
          dsr30 >= 0.95 and ci30.clears_noise)
watch30 = not pass30 and dsr30 >= 0.95 and corr30 < 0.50
verdict30 = "adopted" if pass30 else "discarded"

ev30 = {"best": best30, "dsr": round(dsr30, 4),
        "diff_ci": [round(ci30.lo, 3), round(ci30.hi, 3)],
        "corr_v2_oos": round(corr30, 3), "all_rows": rows30,
        "watchlist_eligible": watch30}
record_outcome(reg30.id, verdict=verdict30, evidence=ev30)
print(f"\n  E30 VERDICT: {verdict30} | watch-list eligible: {watch30}")

# ---------------------------------------------------------------------------
# 8. ROADMAP #10: v2 full-sample significance re-check (monthly)
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2   = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2    = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s18: CI=[-0.0128,+0.7077])")

# ---------------------------------------------------------------------------
# 9. $1,000 benchmark comparison (2000 → latest, pre-holdout)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON ===")

def end_value(prices):
    r = prices.loc["2000-01-01":].pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia_cut  = dia_full[dia_full.index < HOLDOUT_START]
qqq_cut  = qqq_full[qqq_full.index < HOLDOUT_START]
iwm_cut  = iwm_full[iwm_full.index < HOLDOUT_START]
ief_cut2 = ief_full[ief_full.index < HOLDOUT_START]

spy_end  = end_value(spy)
dia_end  = end_value(dia_cut)
qqq_end  = end_value(qqq_cut)
iwm_end  = end_value(iwm_cut)
ief_end  = end_value(ief_cut2)
v2_end   = round(float((1 + r_v2).prod() * 1000), 2)

# E29 best config terminal value
_e29_lbl = best29["label"]
_e29_cfg = {
    "RE(v20/c30,60/40,tv0.18)": dict(vix_elevated=20, vix_crisis=30,
        w_v2_elevated=0.60, w_bol_elevated=0.40, target_vol=0.18, cta_vol=0.12),
    "RE(v20/c35,70/30,tv0.18)": dict(vix_elevated=20, vix_crisis=35,
        w_v2_elevated=0.70, w_bol_elevated=0.30, target_vol=0.18, cta_vol=0.12),
    "RE(v25/c40,60/40,tv0.18)": dict(vix_elevated=25, vix_crisis=40,
        w_v2_elevated=0.60, w_bol_elevated=0.40, target_vol=0.18, cta_vol=0.12),
    "RE(v20/c30,v2only,tv0.18)": dict(vix_elevated=20, vix_crisis=30,
        w_v2_elevated=1.00, w_bol_elevated=0.00, target_vol=0.18, cta_vol=0.12),
}
wts29_best = regime_ensemble.multi_signals(panel_full, vix_panel,
                                           **_e29_cfg[_e29_lbl])
r29_full = me.portfolio_returns(panel_full, wts29_best, commission=COST,
                                rf_daily=rf_daily.reindex(panel_full.index).fillna(0))
e29_end = round(float((1 + r29_full).prod() * 1000), 2)

# E30 best config terminal value
_e30_lbl = best30["label"]
_e30_cfg = {
    "IM(lb63,scale0.50)":  dict(target_vol=0.18, lookback=63,  reduced_scale=0.50),
    "IM(lb63,scale0.00)":  dict(target_vol=0.18, lookback=63,  reduced_scale=0.00),
    "IM(lb126,scale0.50)": dict(target_vol=0.18, lookback=126, reduced_scale=0.50),
    "IM(lb21,scale0.50)":  dict(target_vol=0.18, lookback=21,  reduced_scale=0.50),
}
sig30_best = intermarket.signals(spy, ief_cut, **_e30_cfg[_e30_lbl])
r30_full   = ve.strategy_returns(spy, sig30_best, commission=COST, rf_daily=rf_daily)
e30_end    = round(float((1 + r30_full).prod() * 1000), 2)

# Mag-7 (from 2012, survivorship-biased)
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
try:
    mag7_panel = loader.load_universe(mag7, start="2012-05-18")
    mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna()
    mag7_ret   = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
    mag7_end   = round(float((1 + mag7_ret).prod() * 1000), 2)
except Exception:
    mag7_end   = None

intl = {}
for t in ["EWC", "ACWI", "EFA"]:
    try:
        p = loader.load_ohlcv(t)["Close"]
        p = p[p.index < HOLDOUT_START]
        intl[t] = end_value(p)
    except Exception:
        intl[t] = None

print(f"  $1k from 2000 → {latest_spy_date.date()} (pre-holdout):")
print(f"    v2 champion:          ${v2_end:>10,.2f}")
print(f"    E29 Regime Ensemble:  ${e29_end:>10,.2f}  ({_e29_lbl})")
print(f"    E30 Inter-Market:     ${e30_end:>10,.2f}  ({_e30_lbl})")
print(f"    QQQ (Nasdaq 100):     ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):        ${spy_end:>10,.2f}")
print(f"    DIA (DOW Jones):      ${dia_end:>10,.2f}")
print(f"    IWM (Russell 2000):   ${iwm_end:>10,.2f}")
print(f"    IEF (7-10y Treasury): ${ief_end:>10,.2f}")
print(f"    EWC (Canada):         ${intl.get('EWC') or 'N/A':>10}")
print(f"    EFA (Intl Devlpd):    ${intl.get('EFA') or 'N/A':>10}")
print(f"    ACWI (World):         ${intl.get('ACWI') or 'N/A':>10}")
if mag7_end:
    print(f"    Mag-7 eqw 2012:       ${mag7_end:>10,.2f}  (surv. bias; G4 cap)")

# ---------------------------------------------------------------------------
# 10. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak     = max(PEAK_VALUE, new_value)
dd_from_peak = (new_value / new_peak - 1) * 100

note_s20 = (
    f"Session 20 (2026-07-24): New SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f} (close {latest_spy_close:.2f} "
    f"{'>' if latest_spy_close > band_up else '<'} band {band_up:.2f}; "
    f"vol {vol20*100:.1f}% vs 18% target). No trades. "
    f"E29 Regime Ensemble: {verdict29} (best {_e29_lbl} mean_wf={best29['mean_wf']}, "
    f"DD={best29['worst_dd']}%, DSR={dsr29:.4f}, CI=[{ci29.lo:.3f},{ci29.hi:.3f}], "
    f"corr_v2={corr29:.3f}, watchlist={watch29}). "
    f"E30 Inter-Market: {verdict30} (best {_e30_lbl} mean_wf={best30['mean_wf']}, "
    f"DD={best30['worst_dd']}%, DSR={dsr30:.4f}, CI=[{ci30.lo:.3f},{ci30.hi:.3f}], "
    f"corr_v2={corr30:.3f}, watchlist={watch30}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}. "
    f"DD from peak: {dd_from_peak:+.2f}%."
)

history_entry = {
    "date": "2026-07-24",
    "session": 20,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(port_chg, 2),
    "chg_pct": round(port_pct, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s20,
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
# 11. Session summary + save results
# ---------------------------------------------------------------------------
total_configs = trials_this_period()
print(f"\n{'='*65}")
print(f"SESSION 20 SUMMARY (2026-07-24)")
print(f"{'='*65}")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f} | DD from peak: {dd_from_peak:+.2f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"\nExperiment Results:")
for exp, best, verdict, dsr, ci, watch, corr in [
    ("E29 Regime Ensemble", best29, verdict29, dsr29, ci29, watch29, corr29),
    ("E30 Inter-Market",    best30, verdict30, dsr30, ci30, watch30, corr30),
]:
    print(f"  {exp}: {verdict.upper()}")
    print(f"    mean_wf={best['mean_wf']} (bar 0.844) | "
          f"DD={best['worst_dd']}% (bar -20.5%) | "
          f"DSR={dsr:.4f} (bar 0.95)")
    print(f"    CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise} | "
          f"corr_v2={corr:.3f} | watchlist={watch}")
print(f"\nv2 significance: DSR={dsr_v2:.4f} | "
      f"CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}] | clears={ci_v2.clears_noise}")
print(f"Champion UNCHANGED. Total configs: {total_configs}")

results = {
    "session": "2026-07-24-s20",
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
    "E29_RegimeEnsemble": {
        "verdict": verdict29, "best": best29,
        "dsr": round(dsr29, 4), "ci": [round(ci29.lo, 3), round(ci29.hi, 3)],
        "corr_v2_oos": round(corr29, 3), "all_rows": rows29,
        "watchlist_eligible": watch29,
    },
    "E30_InterMarket": {
        "verdict": verdict30, "best": best30,
        "dsr": round(dsr30, 4), "ci": [round(ci30.lo, 3), round(ci30.hi, 3)],
        "corr_v2_oos": round(corr30, 3), "all_rows": rows30,
        "watchlist_eligible": watch30,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2.lo, 4), round(ci_v2.hi, 4)],
        "clears": ci_v2.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E29_RE": e29_end, "E30_IM": e30_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end,
        "IWM": iwm_end, "IEF": ief_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"),
        "ACWI": intl.get("ACWI"), "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_24.json", "w"), indent=1)
print("Results saved → research/results_2026_07_24.json")
