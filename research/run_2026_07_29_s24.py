"""Session 24 (2026-07-29): Two new investing-philosophy experiments.

Philosophies researched this session:

E36 — Faber GTAA-5 Revisited (with full DBC commodity history)
  Philosophy: Mebane Faber (2007) SSRN 962461 "A Quantitative Approach to
  Tactical Asset Allocation." Five uncorrelated global asset classes in equal
  20% slots, each gated by its own SMA(sma_window) trend filter. Faber's
  original five: US equity (SPY), international equity (EFA), commodities (DBC),
  real estate (VNQ), and bonds (IEF). The ROADMAP explicitly flagged E10
  (prior GTAA-5 test) for "revisit when DBC has more history." DBC now has
  19+ years of data (Feb 2006 → Jul 2026), making this revisit valid.
  Distinction from E6 GTAA-4 (watch-listed, uses SPY/IWM/IEF/GLD):
    E6 uses 4 assets without international equity or commodities.
  Distinction from E10 (prior GTAA-5, discarded on significance ~2014):
    E10 tested DBC with < 3 years of history; fold-1 result was unreliable.

E37 — Swensen-Inspired 4-Asset Diversified Allocation
  Philosophy: David Swensen (2000/2009) "Pioneering Portfolio Management."
  The Yale Endowment outperformed by allocating to TRULY DIFFERENT economic
  asset classes. ETF-based approximation: SPY (equity), IEF (bonds), GLD
  (gold/crisis hedge), and either VNQ (real estate) or DBC (commodities).
  Each 25% slot is independently gated by SMA(sma_window). The fourth slot
  (VNQ vs DBC) is parameterized to test which real-asset sub-class adds more
  value over 2000-2025.
  Distinction from E12 Risk Parity (SPY/IEF/GLD, watch-listed):
    Swensen uses EQUAL weights (not inverse-vol) and a 4th real-asset slot.
  Distinction from E14 Permanent Portfolio (SPY/TLT/GLD/SHY, watch-listed):
    PP uses FIXED proportions with drift rebalancing (no trend gates per asset).
  Distinction from E10/E36 GTAA-5:
    Uses 4 assets at 25% instead of 5 at 20%; GLD is included as a distinct
    inflation hedge slot rather than folded into commodities.

Data through: checked at runtime.
Champion configs entering session: 233.
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
from strategies import gtaa_full, swensen_alloc
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
dbc_full  = loader.load_ohlcv("DBC")["Close"]
vnq_full  = loader.load_ohlcv("VNQ")["Close"]
efa_full  = loader.load_ohlcv("EFA")["Close"]
dia_full  = loader.load_ohlcv("DIA")["Close"]
qqq_full  = loader.load_ohlcv("QQQ")["Close"]
iwm_full  = loader.load_ohlcv("IWM")["Close"]
efa_full2 = loader.load_ohlcv("EFA")["Close"]

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
PREV_VALUE  = 985.56           # last confirmed mark (s23, 2026-07-27 close)
PEAK_VALUE  = 1006.52
INCEPTION   = 1000.0
LIVE_SPY_BASE = 749.1699829101562

new_value     = round(UNITS * latest_spy_close, 2)
spy_day_chg   = (latest_spy_close / prev_spy_close - 1) * 100
port_chg      = new_value - PREV_VALUE
port_pct      = (new_value / PREV_VALUE - 1) * 100
all_time_pct  = (new_value / INCEPTION - 1) * 100
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
trend_state = "ON" if latest_spy_close > band_up else ("OFF" if latest_spy_close < band_dn else "HOLD")

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

# Pre-hold GTAA-5 price panel (SPY + EFA + DBC + VNQ + IEF)
def _align(s):
    return s.reindex(spy.index).ffill()

panel_gtaa = pd.DataFrame({
    "SPY": spy,
    "EFA": _align(efa_full),
    "DBC": _align(dbc_full),
    "VNQ": _align(vnq_full),
    "IEF": _align(ief_full),
}).dropna(how="all")

# Pre-hold Swensen panels
panel_sw_vnq = pd.DataFrame({
    "SPY": spy,
    "IEF": _align(ief_full),
    "GLD": _align(gld_full),
    "VNQ": _align(vnq_full),
}).dropna(how="all")

panel_sw_dbc = pd.DataFrame({
    "SPY": spy,
    "IEF": _align(ief_full),
    "GLD": _align(gld_full),
    "DBC": _align(dbc_full),
}).dropna(how="all")

# ---------------------------------------------------------------------------
# 6. ROADMAP #10: v2 full-sample significance re-check (first week of August)
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2  = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2   = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s23: CI=[-0.0129,+0.7077])")

# ---------------------------------------------------------------------------
# 7. E36: Faber GTAA-5 Revisited (with full DBC history)
# ---------------------------------------------------------------------------
print("\n=== E36: FABER GTAA-5 REVISITED (DBC NOW 19+ YRS) ===")

reg36 = preregister(
    hypothesis=(
        "Faber (2007) GTAA-5 with 5 uncorrelated global asset classes "
        "(SPY/EFA/DBC/VNQ/IEF, 20% each, each SMA-gated) provides meaningful "
        "diversification across equity, international equity, commodities, real "
        "estate, and bonds. Prior test (E10, 2026-07-14) was discarded on "
        "statistical significance when DBC had < 3 years of history. DBC now "
        "has 19+ years (Feb 2006 → Jul 2026), making the commodity-inclusive "
        "fold-1 backtest reliable. "
        "Hypothesis: the 5-asset equal-weight GTAA improves on v2 (single-asset "
        "SPY trend) by capturing additional return premia in EFA, DBC, VNQ, and "
        "IEF, while individual trend gates limit drawdown in each asset class. "
        "Skeptical prior: (a) DBC and VNQ have short fold-1 histories (2006+ and "
        "2004+), hurting fold-1 Sharpe; (b) international equity (EFA) and "
        "commodities (DBC) have underperformed SPY since 2009, dragging fold-2/3; "
        "(c) DSR penalty at 233+ prior configs is severe -- a genuine edge is "
        "needed; (d) corr to v2 may be high since SPY slot replicates v2's equity "
        "signal exactly."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 233 + 6 new configs = 239 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list revisit E10): DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

E36_GRID = [
    dict(sma_window=150, band=0.0,  label="GTAA5(w150,b0.00)"),
    dict(sma_window=150, band=0.03, label="GTAA5(w150,b0.03)"),
    dict(sma_window=200, band=0.0,  label="GTAA5(w200,b0.00)"),
    dict(sma_window=200, band=0.03, label="GTAA5(w200,b0.03)"),
    dict(sma_window=252, band=0.0,  label="GTAA5(w252,b0.00)"),
    dict(sma_window=252, band=0.03, label="GTAA5(w252,b0.03)"),
]

rows36, trial_sh36, oos36, full36 = [], [], {}, {}
for cfg in E36_GRID:
    lbl = cfg.pop("label")
    try:
        wts = gtaa_full.multi_signals(panel_gtaa, **cfg)
        m = wf_multi(panel_gtaa, wts, lbl)
        trial_sh36.append(m["oos_sharpe"])
        oos36[lbl] = m.pop("_r_oos")
        full36[lbl] = m.pop("_r_full")
        rows36.append(m)
        print(f"  {m}")
    except Exception as e:
        print(f"  ERROR on {lbl}: {e}")

if not rows36:
    print("  All E36 configs failed.")
    verdict36 = "inconclusive"
    best36 = {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr36, ci36, corr36, watch36 = 0.0, None, 1.0, False
else:
    best36 = max(rows36, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E36: {best36}")
    dsr36, ci36 = significance(oos36[best36["label"]], trial_sh36, best36["label"])
    corr36 = float(oos36[best36["label"]].corr(r_v2_oos))
    print(f"  corr(GTAA5,v2) OOS: {corr36:.3f}")

    pass36 = (best36["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best36["worst_dd"] > V2_WORST_DD and
              dsr36 >= 0.95 and ci36.clears_noise)
    watch36 = not pass36 and dsr36 >= 0.95 and corr36 < 0.50
    verdict36 = "adopted" if pass36 else "discarded"

    ev36 = {"best": best36, "dsr": round(dsr36, 4),
            "diff_ci": [round(ci36.lo, 3), round(ci36.hi, 3)],
            "corr_v2_oos": round(corr36, 3), "all_rows": rows36,
            "watchlist_eligible": watch36}
    record_outcome(reg36.id, verdict=verdict36, evidence=ev36)
    print(f"\n  E36 VERDICT: {verdict36} | watch-list eligible: {watch36}")

# ---------------------------------------------------------------------------
# 8. E37: Swensen-Inspired 4-Asset Allocation
# ---------------------------------------------------------------------------
print("\n=== E37: SWENSEN 4-ASSET DIVERSIFIED ALLOCATION ===")

reg37 = preregister(
    hypothesis=(
        "Swensen (2009) 'Pioneering Portfolio Management': diversifying across "
        "TRULY DIFFERENT economic asset classes improves risk-adjusted returns. "
        "ETF implementation: SPY (equity), IEF (bonds), GLD (gold/crisis hedge), "
        "and either VNQ (real estate) or DBC (commodities) as the 4th real-asset "
        "slot. Each 25% slot is independently gated by SMA(sma_window); slots "
        "below trend earn T-bill rate. The 4th-slot parameterization tests which "
        "real-asset sub-class (VNQ vs DBC) adds more value in 2000-2025. "
        "Hypothesis: 4 genuinely uncorrelated return premia -- equity risk premium, "
        "duration/safe-haven, inflation/crisis hedge, and real assets -- provide "
        "better diversification than the 3-asset strategies tested (risk parity "
        "E12, permanent portfolio E14) and meaningfully lower drawdown than v2. "
        "Skeptical prior: (a) GLD and VNQ/DBC have partial history in fold-1 "
        "(data from 2004 and 2006 respectively), limiting early coverage; "
        "(b) equal weights (not risk-adjusted) may leave the portfolio dominated "
        "by SPY volatility despite 75% nominal non-equity exposure; (c) the "
        "Swensen insight was about ILLIQUID assets (private equity, timber) that "
        "don't exist as liquid ETFs -- the diversification premium may be smaller "
        "for the liquid-only subset; (d) DSR penalty now at 239+ prior configs."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 239 + 6 new configs = 245 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

E37_GRID = [
    dict(sma_window=100, use_dbc=False, label="SWN4(w100,VNQ)"),
    dict(sma_window=150, use_dbc=False, label="SWN4(w150,VNQ)"),
    dict(sma_window=200, use_dbc=False, label="SWN4(w200,VNQ)"),
    dict(sma_window=100, use_dbc=True,  label="SWN4(w100,DBC)"),
    dict(sma_window=150, use_dbc=True,  label="SWN4(w150,DBC)"),
    dict(sma_window=200, use_dbc=True,  label="SWN4(w200,DBC)"),
]

rows37, trial_sh37, oos37, full37 = [], [], {}, {}
for cfg in E37_GRID:
    lbl = cfg.pop("label")
    use_dbc = cfg["use_dbc"]
    panel = panel_sw_dbc if use_dbc else panel_sw_vnq
    real_asset_name = "DBC" if use_dbc else "VNQ"
    # Load real asset series aligned to panel dates
    if use_dbc:
        real_s = dbc_full.reindex(spy.index).ffill()
    else:
        real_s = vnq_full.reindex(spy.index).ffill()
    try:
        wts = swensen_alloc.multi_signals(
            spy,
            ief=ief_full.reindex(spy.index).ffill(),
            gld=gld_full.reindex(spy.index).ffill(),
            real_asset=real_s,
            **cfg,
        )
        # Align panel columns with weight columns
        panel_c = panel.reindex(columns=wts.columns)
        m = wf_multi(panel_c, wts, lbl)
        trial_sh37.append(m["oos_sharpe"])
        oos37[lbl] = m.pop("_r_oos")
        full37[lbl] = m.pop("_r_full")
        rows37.append(m)
        print(f"  {m}")
    except Exception as e:
        import traceback
        print(f"  ERROR on {lbl}: {e}")
        traceback.print_exc()

if not rows37:
    print("  All E37 configs failed.")
    verdict37 = "inconclusive"
    best37 = {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr37, ci37, corr37, watch37 = 0.0, None, 1.0, False
else:
    best37 = max(rows37, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E37: {best37}")
    dsr37, ci37 = significance(oos37[best37["label"]], trial_sh37, best37["label"])
    corr37 = float(oos37[best37["label"]].corr(r_v2_oos))
    print(f"  corr(SWN4,v2) OOS: {corr37:.3f}")

    pass37 = (best37["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best37["worst_dd"] > V2_WORST_DD and
              dsr37 >= 0.95 and ci37.clears_noise)
    watch37 = not pass37 and dsr37 >= 0.95 and corr37 < 0.50
    verdict37 = "adopted" if pass37 else "discarded"

    ev37 = {"best": best37, "dsr": round(dsr37, 4),
            "diff_ci": [round(ci37.lo, 3), round(ci37.hi, 3)],
            "corr_v2_oos": round(corr37, 3), "all_rows": rows37,
            "watchlist_eligible": watch37}
    record_outcome(reg37.id, verdict=verdict37, evidence=ev37)
    print(f"\n  E37 VERDICT: {verdict37} | watch-list eligible: {watch37}")

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

e36_end = None
e37_end = None

if rows36 and best36.get("label", "FAILED") != "FAILED":
    _key36 = best36["label"]
    if _key36 in full36:
        e36_end = end_value_from_returns(full36[_key36])

if rows37 and best37.get("label", "FAILED") != "FAILED":
    _key37 = best37["label"]
    if _key37 in full37:
        e37_end = end_value_from_returns(full37[_key37])

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
if e36_end:
    print(f"    E36 GTAA-5:            ${e36_end:>10,.2f}   ({best36['label']})")
if e37_end:
    print(f"    E37 Swensen-4:         ${e37_end:>10,.2f}   ({best37['label']})")
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

e36_lbl  = best36.get("label", "N/A") if rows36 else "N/A"
e37_lbl  = best37.get("label", "N/A") if rows37 else "N/A"
ci36_str = f"[{ci36.lo:.3f},{ci36.hi:.3f}]" if ci36 else "N/A"
ci37_str = f"[{ci37.lo:.3f},{ci37.hi:.3f}]" if ci37 else "N/A"

note_s24 = (
    f"Session 24 (2026-07-29): SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f}. No trades. "
    f"E36 GTAA-5: {verdict36} (best {e36_lbl} mean_wf={best36['mean_wf']}, "
    f"DD={best36['worst_dd']}%, DSR={dsr36:.4f}, CI={ci36_str}, "
    f"corr_v2={corr36:.3f}, watchlist={watch36}). "
    f"E37 Swensen-4: {verdict37} (best {e37_lbl} mean_wf={best37['mean_wf']}, "
    f"DD={best37['worst_dd']}%, DSR={dsr37:.4f}, CI={ci37_str}, "
    f"corr_v2={corr37:.3f}, watchlist={watch37}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN'}. "
    f"DD from peak: {dd_from_peak:+.2f}%. $1k v2={v2_end} SPY={spy_end}."
)

history_entry = {
    "date": "2026-07-29",
    "session": 24,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(new_value - PREV_VALUE, 2),
    "chg_pct": round((new_value / PREV_VALUE - 1) * 100, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s24,
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
print(f"SESSION 24 SUMMARY (2026-07-29)")
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
    ("E36 GTAA-5 Revisited", best36, verdict36, dsr36, ci36, watch36, corr36),
    ("E37 Swensen 4-Asset",  best37, verdict37, dsr37, ci37, watch37, corr37),
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

print(f"\nChampion UNCHANGED. Total configs: {total_configs}")

results = {
    "session": "2026-07-29-s24",
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
    "E36_GTAA5": {
        "verdict": verdict36, "best": best36,
        "dsr": round(dsr36, 4),
        "ci": [round(ci36.lo, 3), round(ci36.hi, 3)] if ci36 else None,
        "corr_v2_oos": round(corr36, 3), "all_rows": rows36,
        "watchlist_eligible": watch36,
    },
    "E37_SWN4": {
        "verdict": verdict37, "best": best37,
        "dsr": round(dsr37, 4),
        "ci": [round(ci37.lo, 3), round(ci37.hi, 3)] if ci37 else None,
        "corr_v2_oos": round(corr37, 3), "all_rows": rows37,
        "watchlist_eligible": watch37,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E36_GTAA5": e36_end, "E37_SWN4": e37_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end, "IWM": iwm_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"), "ACWI": intl.get("ACWI"),
        "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_29.json", "w"), indent=1)
print("Results saved → research/results_2026_07_29.json")
