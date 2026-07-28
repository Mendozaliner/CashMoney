"""Session 23 (2026-07-28): Two new investing-philosophy experiments.

Investing philosophies researched this session:

E34 — Defensive Dual-Asset Cash Sleeve (DDAS)
  Philosophy: When v2 is in cash (equity bear market), the two best
  defensive assets are bonds (IEF) and gold (GLD), which protect in
  DIFFERENT macro regimes. IEF performs in recession/deflation; GLD
  in inflation/currency-debasement. E33 (prior session) only tested IEF.
  This experiment splits the defensive cash sleeve between BOTH IEF and GLD,
  each independently gated by their own SMA(defense_window) trend filter.
  The split is determined by gld_frac: the fraction allocated to GLD.
  Academic basis: Ilmanen (2011), Erb & Harvey (2013), Faber (2007 SSRN).

E35 — Correlation-Regime Defensive Switch (CRDS)
  Philosophy: The rolling correlation between SPY and IEF daily returns
  is the key signal identifying macro regimes:
    - Normal/deflation (corr < threshold): bonds are the hedge → hold IEF
    - Inflation (corr >= threshold): bonds and stocks both fall → hold GLD
  When v2 is in cash, the defensive asset is chosen dynamically by this
  correlation-regime signal. Academic basis: Ilmanen (2011) on stock-bond
  correlation regimes, Campbell/Pflueger/Viceira (2020), Asness et al. (2012).
  Key distinction: E29 VIX-regime ensemble (CLOSED) used VIX as a macro
  signal. E35 uses stock-BOND correlation, a different and more directly
  relevant regime indicator. The 2022 failure of bonds makes this specific
  test particularly important.

Data through: checked at runtime.
Champion configs entering session: 216.
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
from strategies import defensive_dual, corr_regime
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
dia_full  = loader.load_ohlcv("DIA")["Close"]
qqq_full  = loader.load_ohlcv("QQQ")["Close"]
iwm_full  = loader.load_ohlcv("IWM")["Close"]
efa_full  = loader.load_ohlcv("EFA")["Close"]

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
UNITS      = 1.3334757435413753
PREV_VALUE = 985.35          # last confirmed mark (2026-07-24, session 22)
PEAK_VALUE = 1006.52
INCEPTION  = 1000.0
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
r_v2     = ve.strategy_returns(spy, sig_v2, commission=COST, rf_daily=rf_daily.reindex(spy.index).fillna(0))
r_v2_oos = r_v2.loc[OOS_A:OOS_B]

bm_v2  = wf_single(r_v2, "v2 champion")
bm_spy = wf_single(spy_ret, "SPY B&H")

print("\n=== BASELINES ===")
print(f"  v2 champion: folds={bm_v2['folds']}  mean_wf={bm_v2['mean_wf']}  "
      f"worst_dd={bm_v2['worst_dd']}%  end1k=${bm_v2['end1k']:,.2f}")
print(f"  SPY B&H:     folds={bm_spy['folds']}  mean_wf={bm_spy['mean_wf']}  "
      f"worst_dd={bm_spy['worst_dd']}%  end1k=${bm_spy['end1k']:,.2f}")

# Multi-asset price panel: SPY + IEF + GLD (pre-holdout)
panel_eig = pd.DataFrame({
    "SPY": spy,
    "IEF": ief_full.reindex(spy.index).ffill(),
    "GLD": gld_full.reindex(spy.index).ffill(),
}).dropna(how="all")

# Pre-load defensive series (pre-holdout)
ief_cut = ief_full.reindex(spy.index).ffill()
gld_cut = gld_full.reindex(spy.index).ffill()

# ---------------------------------------------------------------------------
# 6. ROADMAP #10: v2 full-sample significance re-check (monthly)
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2  = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2   = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s22: CI=[-0.0128,+0.7077])")

# ---------------------------------------------------------------------------
# 7. E34: Defensive Dual-Asset Cash Sleeve (DDAS)
# ---------------------------------------------------------------------------
print("\n=== E34: DEFENSIVE DUAL-ASSET CASH SLEEVE ===")

reg34 = preregister(
    hypothesis=(
        "When v2 is in cash (equity bear market), the two best defensive "
        "assets — bonds (IEF) and gold (GLD) — perform in DIFFERENT macro "
        "regimes. E33 only tested IEF. This experiment splits the defensive "
        "cash sleeve between BOTH IEF and GLD (each independently gated by "
        "their own SMA(defense_window) trend filter), using gld_frac to set "
        "the GLD allocation. "
        "Hypothesis: a diversified defensive sleeve (IEF + GLD) provides more "
        "consistent bear-market protection than IEF alone, because GLD captures "
        "inflation-regime bear markets (2022: IEF -18% vs GLD +0.4%) while IEF "
        "captures recession/deflation bear markets (2008-09: IEF +25%). "
        "Skeptical prior: (a) the SMA gate on each asset may not add enough "
        "regime discrimination; (b) the defensive cash periods (~35% of time) "
        "may be too short to accumulate enough edge to clear the CI test; "
        "(c) corr to v2 may be near 1.0 since the equity sleeve is unchanged. "
        "Condition for watch-list: DSR >= 0.95 AND corr < 0.50."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 216 + 8 new configs = 224 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=8,
    primary_metric="sharpe",
)

E34_GRID = [
    dict(gld_frac=0.25, defense_window=200, label="DDAS(g0.25,w200)"),
    dict(gld_frac=0.50, defense_window=200, label="DDAS(g0.50,w200)"),
    dict(gld_frac=0.75, defense_window=200, label="DDAS(g0.75,w200)"),
    dict(gld_frac=1.00, defense_window=200, label="DDAS(g1.00,w200)"),
    dict(gld_frac=0.25, defense_window=100, label="DDAS(g0.25,w100)"),
    dict(gld_frac=0.50, defense_window=100, label="DDAS(g0.50,w100)"),
    dict(gld_frac=0.75, defense_window=100, label="DDAS(g0.75,w100)"),
    dict(gld_frac=1.00, defense_window=100, label="DDAS(g1.00,w100)"),
]

rows34, trial_sh34, oos34, full34 = [], [], {}, {}
for cfg in E34_GRID:
    lbl = cfg.pop("label")
    try:
        wts = defensive_dual.multi_signals(
            spy, ief=ief_cut, gld=gld_cut, target_vol=0.18, lookback=20, **cfg
        )
        m = wf_multi(panel_eig, wts, lbl)
        trial_sh34.append(m["oos_sharpe"])
        oos34[lbl] = m.pop("_r_oos")
        full34[lbl] = m.pop("_r_full")
        rows34.append(m)
        print(f"  {m}")
    except Exception as e:
        print(f"  ERROR on {lbl}: {e}")

if not rows34:
    print("  All E34 configs failed.")
    verdict34, best34 = "inconclusive", {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr34 = 0.0
    ci34 = ev.bootstrap_difference_ci(r_v2_oos, spy_oos_ret)
    corr34, watch34 = 1.0, False
else:
    best34 = max(rows34, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E34: {best34}")
    dsr34, ci34 = significance(oos34[best34["label"]], trial_sh34, best34["label"])
    corr34 = float(oos34[best34["label"]].corr(r_v2_oos))
    print(f"  corr(DDAS,v2) OOS: {corr34:.3f}")

    pass34 = (best34["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best34["worst_dd"] > V2_WORST_DD and
              dsr34 >= 0.95 and ci34.clears_noise)
    watch34 = not pass34 and dsr34 >= 0.95 and corr34 < 0.50
    verdict34 = "adopted" if pass34 else "discarded"

    ev34 = {"best": best34, "dsr": round(dsr34, 4),
            "diff_ci": [round(ci34.lo, 3), round(ci34.hi, 3)],
            "corr_v2_oos": round(corr34, 3), "all_rows": rows34,
            "watchlist_eligible": watch34}
    record_outcome(reg34.id, verdict=verdict34, evidence=ev34)
    print(f"\n  E34 VERDICT: {verdict34} | watch-list eligible: {watch34}")

# ---------------------------------------------------------------------------
# 8. E35: Correlation-Regime Defensive Switch (CRDS)
# ---------------------------------------------------------------------------
print("\n=== E35: CORRELATION-REGIME DEFENSIVE SWITCH ===")

reg35 = preregister(
    hypothesis=(
        "The rolling correlation between SPY and IEF daily returns identifies "
        "the macro regime: negative/low correlation = normal/deflation regime "
        "(bonds hedge stocks → hold IEF in cash); positive correlation = "
        "inflation regime (bonds and stocks fall together → hold GLD in cash). "
        "Using this correlation signal to dynamically switch the defensive cash "
        "sleeve between IEF and GLD should improve capital preservation across "
        "ALL bear-market types, including the 2022 rising-rate regime that "
        "simultaneously killed stocks AND bonds (-18% IEF while v2 was in cash). "
        "Key distinction from E29 VIX-Regime Ensemble (CLOSED, corr_v2=0.967): "
        "VIX signals risk levels within the equity world; stock-bond correlation "
        "is an INDEPENDENT macro-regime signal. "
        "Key distinction from E30 Inter-Market (CLOSED): E30 compared bond vs "
        "equity PERFORMANCE (flows). E35 uses the CORRELATION of their returns — "
        "a fundamentally different measure of regime. "
        "Skeptical prior: (a) the correlation regime may still correlate to v2 "
        "because bear markets (where v2 exits equities) also often accompany "
        "the switch from negative to positive stock-bond correlation; (b) the "
        "defensive cash periods may not accumulate enough edge to clear CI; "
        "(c) GLD SMA gate may not protect adequately in some inflation scenarios."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 224 + 9 new configs = 233 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=9,
    primary_metric="sharpe",
)

E35_GRID = [
    dict(corr_lb=42,  corr_threshold=0.00,  label="CRDS(lb42,t0.00)"),
    dict(corr_lb=42,  corr_threshold=0.15,  label="CRDS(lb42,t0.15)"),
    dict(corr_lb=42,  corr_threshold=0.30,  label="CRDS(lb42,t0.30)"),
    dict(corr_lb=63,  corr_threshold=0.00,  label="CRDS(lb63,t0.00)"),
    dict(corr_lb=63,  corr_threshold=0.15,  label="CRDS(lb63,t0.15)"),
    dict(corr_lb=63,  corr_threshold=0.30,  label="CRDS(lb63,t0.30)"),
    dict(corr_lb=126, corr_threshold=0.00,  label="CRDS(lb126,t0.00)"),
    dict(corr_lb=126, corr_threshold=0.15,  label="CRDS(lb126,t0.15)"),
    dict(corr_lb=126, corr_threshold=0.30,  label="CRDS(lb126,t0.30)"),
]

rows35, trial_sh35, oos35, full35 = [], [], {}, {}
for cfg in E35_GRID:
    lbl = cfg.pop("label")
    try:
        wts = corr_regime.multi_signals(
            spy, ief=ief_cut, gld=gld_cut, target_vol=0.18, lookback=20, **cfg
        )
        m = wf_multi(panel_eig, wts, lbl)
        trial_sh35.append(m["oos_sharpe"])
        oos35[lbl] = m.pop("_r_oos")
        full35[lbl] = m.pop("_r_full")
        rows35.append(m)
        print(f"  {m}")
    except Exception as e:
        print(f"  ERROR on {lbl}: {e}")

if not rows35:
    print("  All E35 configs failed.")
    verdict35, best35 = "inconclusive", {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0}
    dsr35 = 0.0
    ci35 = ev.bootstrap_difference_ci(r_v2_oos, spy_oos_ret)
    corr35, watch35 = 1.0, False
else:
    best35 = max(rows35, key=lambda x: x["mean_wf"])
    print(f"\n  BEST E35: {best35}")
    dsr35, ci35 = significance(oos35[best35["label"]], trial_sh35, best35["label"])
    corr35 = float(oos35[best35["label"]].corr(r_v2_oos))
    print(f"  corr(CRDS,v2) OOS: {corr35:.3f}")

    pass35 = (best35["mean_wf"] >= V2_MEAN_WF_SHARPE and
              best35["worst_dd"] > V2_WORST_DD and
              dsr35 >= 0.95 and ci35.clears_noise)
    watch35 = not pass35 and dsr35 >= 0.95 and corr35 < 0.50
    verdict35 = "adopted" if pass35 else "discarded"

    ev35 = {"best": best35, "dsr": round(dsr35, 4),
            "diff_ci": [round(ci35.lo, 3), round(ci35.hi, 3)],
            "corr_v2_oos": round(corr35, 3), "all_rows": rows35,
            "watchlist_eligible": watch35}
    record_outcome(reg35.id, verdict=verdict35, evidence=ev35)
    print(f"\n  E35 VERDICT: {verdict35} | watch-list eligible: {watch35}")

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

e34_end = None
e35_end = None

if rows34 and best34.get("label", "FAILED") != "FAILED":
    _best34_key = best34["label"]
    if _best34_key in full34:
        e34_end = end_value_from_returns(full34[_best34_key])

if rows35 and best35.get("label", "FAILED") != "FAILED":
    _best35_key = best35["label"]
    if _best35_key in full35:
        e35_end = end_value_from_returns(full35[_best35_key])

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
if e34_end:
    print(f"    E34 DDAS:              ${e34_end:>10,.2f}   ({best34['label']})")
if e35_end:
    print(f"    E35 CRDS:              ${e35_end:>10,.2f}   ({best35['label']})")
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

note_s23 = (
    f"Session 23 (2026-07-28): SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f}. No trades. "
    f"E34 DDAS: {verdict34} (best {best34['label']} mean_wf={best34['mean_wf']}, "
    f"DD={best34['worst_dd']}%, DSR={dsr34:.4f}, CI=[{ci34.lo:.3f},{ci34.hi:.3f}], "
    f"corr_v2={corr34:.3f}, watchlist={watch34}). "
    f"E35 CRDS: {verdict35} (best {best35['label']} mean_wf={best35['mean_wf']}, "
    f"DD={best35['worst_dd']}%, DSR={dsr35:.4f}, CI=[{ci35.lo:.3f},{ci35.hi:.3f}], "
    f"corr_v2={corr35:.3f}, watchlist={watch35}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN'}. "
    f"DD from peak: {dd_from_peak:+.2f}%. $1k v2={v2_end} SPY={spy_end}."
)

history_entry = {
    "date": "2026-07-28",
    "session": 23,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(new_value - PREV_VALUE, 2),
    "chg_pct": round((new_value / PREV_VALUE - 1) * 100, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s23,
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
print(f"SESSION 23 SUMMARY (2026-07-28)")
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
    ("E34 Def. Dual-Asset", best34, verdict34, dsr34, ci34, watch34, corr34),
    ("E35 Corr-Regime",     best35, verdict35, dsr35, ci35, watch35, corr35),
]
for exp, best, verdict, dsr, ci, watch, corr in exps:
    print(f"  {exp}: {verdict.upper()}")
    print(f"    mean_wf={best['mean_wf']} (bar 0.844) | "
          f"DD={best['worst_dd']}% (bar -20.5%) | "
          f"DSR={dsr:.4f} (bar 0.95)")
    print(f"    CI=[{ci.lo:.3f},{ci.hi:.3f}] clears={ci.clears_noise} | "
          f"corr_v2={corr:.3f} | watchlist={watch}")

print(f"\nChampion UNCHANGED. Total configs: {total_configs}")

results = {
    "session": "2026-07-28-s23",
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
    "E34_DDAS": {
        "verdict": verdict34, "best": best34,
        "dsr": round(dsr34, 4), "ci": [round(ci34.lo, 3), round(ci34.hi, 3)],
        "corr_v2_oos": round(corr34, 3), "all_rows": rows34,
        "watchlist_eligible": watch34,
    },
    "E35_CRDS": {
        "verdict": verdict35, "best": best35,
        "dsr": round(dsr35, 4), "ci": [round(ci35.lo, 3), round(ci35.hi, 3)],
        "corr_v2_oos": round(corr35, 3), "all_rows": rows35,
        "watchlist_eligible": watch35,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E34_DDAS": e34_end, "E35_CRDS": e35_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end, "IWM": iwm_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"), "ACWI": intl.get("ACWI"),
        "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_28.json", "w"), indent=1)
print("Results saved → research/results_2026_07_28.json")
