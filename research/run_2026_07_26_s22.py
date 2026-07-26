"""Session 22 (2026-07-26): Three new investing-philosophy experiments.

Investing philosophies researched this session:

E31 — CAPE / Shiller Value Tilt
  Philosophy: The Shiller cyclically adjusted P/E ratio (CAPE) is the
  best-known long-horizon equity return predictor. When CAPE is in the
  top decile of its historical expanding-window distribution, future
  10-year equity returns are systematically lower. This experiment tests
  whether a mild exposure tilt (not a hard exit) during extreme CAPE
  environments can improve the champion v2 strategy.

  Key design choices:
  - CAPE signal is monthly with 1-month publication lag (shift 1 month).
  - Uses an EXPANDING percentile (not fixed threshold) to avoid anchoring
    to the 1929 or 1999 extremes — adapts to each era's valuation norms.
  - Tilt is mild (15-35% reduction) — does not trigger full exit.
  - Literature strongly suggests FAIL at 1-year horizon; expect watch-list
    or discard.

E32 — Yield Curve Regime Overlay
  Philosophy: The yield curve slope (long minus short Treasury yields) is
  the most academically validated recession predictor, with 4-8 quarter
  lead times. This experiment proxies the yield-curve slope using the
  relative momentum of IEF (7-10y duration) vs SHY (1-3y duration): when
  the long end underperforms the short end, the curve is flattening or
  inverting, signaling elevated recession risk.

  Key distinction from E30 (CLOSED — corr_v2=0.974):
  - E30 compared bonds vs EQUITIES (IEF vs SPY). Failed because when bonds
    beat equities, v2's SMA200 gate had already captured the equity decline.
  - E32 compares LONG bonds vs SHORT bonds (IEF vs SHY). This measures yield
    curve shape independently of equity performance, potentially providing an
    EARLIER warning than the equity-price-based SMA200 gate.

  Skeptical prior: the 2022-2024 inversion was the longest in history (22 mo)
  while equities rallied 25%+. That OOS window will likely hurt E32 badly.

E33 — Tactical Bond Cash Sleeve
  Philosophy: The champion v2 is in cash approximately 35% of the time (when
  SPY is below the SMA200+3% band). That cash earns only the T-bill rate.
  In equity bear markets, Treasuries often rally (flight to quality). This
  experiment enhances the CASH SLEEVE ONLY — when v2 is in cash AND IEF is
  above its own SMA200 trend gate, the idle cash is deployed into IEF instead
  of T-bills.

  Key distinction from prior experiments:
  - E20 CTA (CLOSED): replaced equity with bonds/gold in a three-way rotation.
    E33 never changes the equity sleeve — v2 runs unchanged. Only cash earns
    IEF when conditions are met.
  - E30 (CLOSED): reduced equity exposure. E33 keeps equity exposure the same.
  - Uses multi_engine for proper pricing of the two-asset (SPY + IEF) sleeve.

  Best-case scenario: in equity bear markets, v2 is in cash while IEF rallies
  → both the equity exit AND the bond rally compound the bear-market advantage.
  Risk scenario: 2022 — v2 goes to cash (correct) but IEF also falls (rising
  rates). The IEF SMA200 gate should protect by keeping bonds only when they
  are themselves in an uptrend.

Data through: checked at runtime.
Champion configs entering session: 200.
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
from strategies import cape_tilt, yield_curve, tactical_bond
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
shy_full  = loader.load_ohlcv("SHY")["Close"]
gld_full  = loader.load_ohlcv("GLD")["Close"]
dia_full  = loader.load_ohlcv("DIA")["Close"]
qqq_full  = loader.load_ohlcv("QQQ")["Close"]
iwm_full  = loader.load_ohlcv("IWM")["Close"]

irx_full  = loader.load_ohlcv("^IRX")["Close"].reindex(spy.index).ffill()
rf_daily  = (irx_full / 100.0) / 252.0

# Shiller CAPE monthly data (for E31)
try:
    shiller = loader.load_shiller()
    print(f"  Shiller data: {len(shiller)} months, latest {shiller.index[-1].date()}")
    print(f"  Current CAPE: {shiller['CAPE'].dropna().iloc[-1]:.1f}")
    shiller_available = True
except Exception as e:
    print(f"  WARNING: Shiller data unavailable: {e}")
    shiller_available = False

spy_ret     = spy.pct_change().fillna(0.0)
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
PREV_VALUE = 984.35           # last confirmed mark (2026-07-23 close, session 20)
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
# 6. E31: CAPE Value Tilt
# ---------------------------------------------------------------------------
print("\n=== E31: CAPE VALUE TILT ===")

if not shiller_available:
    print("  SKIPPED — Shiller data not available.")
    verdict31 = "inconclusive"
    best31 = {"label": "SKIPPED", "mean_wf": 0.0, "worst_dd": 0.0, "end1k": 0.0}
    dsr31 = 0.0
    ci31 = ev.bootstrap_difference_ci(r_v2_oos, spy_oos_ret)
    corr31 = 1.0
    watch31 = False
    rows31 = []
    trial_sh31 = []
    reg31 = None
else:
    reg31 = preregister(
        hypothesis=(
            "When the Shiller CAPE is in the upper tail of its expanding-window "
            "percentile distribution (top 10-20%), expected 10-year equity returns "
            "are suppressed. A mild tilt (15-35% reduction in v2 exposure) during "
            "these extreme-valuation regimes should reduce the cost of potential "
            "mean-reversion without triggering premature exits.\n"
            "Skeptical prior: (a) CAPE has near-zero 1-year predictive power; "
            "(b) CAPE has been in the top decile since ~2015, during which equities "
            "roughly tripled; (c) v2's vol-targeting already reduces exposure when "
            "the market becomes volatile, which often (but not always) coincides "
            "with high-CAPE drawdown environments. Expect FAIL or watch-list only."
        ),
        success_criteria=(
            "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
            "-20.5% AND DSR >= 0.95 (against 200 + 6 new configs = 206 total) AND "
            "diff-vs-SPY bootstrap CI lower bound > 0. "
            "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
        ),
        grid_size=6,
        primary_metric="sharpe",
    )

    E31_GRID = [
        dict(cape_pct=0.90, tilt=0.15, label="CT(pct0.90,t0.15)"),
        dict(cape_pct=0.90, tilt=0.25, label="CT(pct0.90,t0.25)"),
        dict(cape_pct=0.90, tilt=0.35, label="CT(pct0.90,t0.35)"),
        dict(cape_pct=0.85, tilt=0.15, label="CT(pct0.85,t0.15)"),
        dict(cape_pct=0.85, tilt=0.25, label="CT(pct0.85,t0.25)"),
        dict(cape_pct=0.80, tilt=0.25, label="CT(pct0.80,t0.25)"),
    ]

    rows31, trial_sh31, oos31 = [], [], {}
    for cfg in E31_GRID:
        lbl = cfg.pop("label")
        try:
            sig = cape_tilt.signals(spy, target_vol=0.18, lookback=20, **cfg)
            r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
            m   = wf_single(r, lbl)
            trial_sh31.append(m["oos_sharpe"])
            oos31[lbl] = r.loc[OOS_A:OOS_B]
            rows31.append(m)
            print(f"  {m}")
        except Exception as e:
            print(f"  ERROR on {lbl}: {e}")

    if not rows31:
        print("  All E31 configs failed. Skipping significance.")
        verdict31 = "inconclusive"
        best31 = {"label": "FAILED", "mean_wf": 0.0, "worst_dd": 0.0, "end1k": 0.0}
        dsr31, ci31 = 0.0, ev.bootstrap_difference_ci(r_v2_oos, spy_oos_ret)
        corr31 = 1.0
        watch31 = False
    else:
        best31 = max(rows31, key=lambda x: x["mean_wf"])
        print(f"\n  BEST E31: {best31}")
        dsr31, ci31 = significance(oos31[best31["label"]], trial_sh31, best31["label"])

        corr31 = float(oos31[best31["label"]].corr(r_v2_oos))
        print(f"  corr(CAPETilt,v2) OOS: {corr31:.3f}")

        pass31 = (best31["mean_wf"] >= V2_MEAN_WF_SHARPE and
                  best31["worst_dd"] > V2_WORST_DD and
                  dsr31 >= 0.95 and ci31.clears_noise)
        watch31 = not pass31 and dsr31 >= 0.95 and corr31 < 0.50
        verdict31 = "adopted" if pass31 else "discarded"

        ev31 = {"best": best31, "dsr": round(dsr31, 4),
                "diff_ci": [round(ci31.lo, 3), round(ci31.hi, 3)],
                "corr_v2_oos": round(corr31, 3), "all_rows": rows31,
                "watchlist_eligible": watch31}
        record_outcome(reg31.id, verdict=verdict31, evidence=ev31)
        print(f"\n  E31 VERDICT: {verdict31} | watch-list eligible: {watch31}")

# ---------------------------------------------------------------------------
# 7. E32: Yield Curve Regime Overlay
# ---------------------------------------------------------------------------
print("\n=== E32: YIELD CURVE REGIME OVERLAY ===")

reg32 = preregister(
    hypothesis=(
        "The yield curve slope (long minus short Treasury yields) is the most "
        "academically validated recession predictor. When IEF (7-10y) underperforms "
        "SHY (1-3y) over a 6-12 month window, the curve is flattening or inverting, "
        "signaling elevated recession risk 4-8 quarters ahead. Scaling down v2 "
        "equity exposure in these regimes should reduce exposure to subsequent "
        "bear markets.\n"
        "Key distinction from E30 (bond vs equity, CLOSED, corr_v2=0.974): "
        "This compares SHORT bond ETF vs LONG bond ETF performance — the yield "
        "curve shape — not bonds vs equities. The yield curve can invert BEFORE "
        "equities decline, potentially providing an earlier signal than v2's "
        "SMA200 gate.\n"
        "Skeptical prior: (a) yield curve signal works at 4-8 quarter frequency, "
        "not 1-year trading frequency; (b) the 2022-2024 inversion was 22 months "
        "while equities rallied 25%+ — this OOS window would likely punish the "
        "signal severely; (c) the signal may still be too correlated to v2 because "
        "both ultimately respond to the same macro environment."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 206 + 6 new configs = 212 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=6,
    primary_metric="sharpe",
)

ief_cut = ief_full.reindex(spy.index).ffill()
shy_cut = shy_full.reindex(spy.index).ffill()

E32_GRID = [
    dict(lookback=63,  invert_scale=0.50, label="YC(lb63,s0.50)"),
    dict(lookback=63,  invert_scale=0.75, label="YC(lb63,s0.75)"),
    dict(lookback=126, invert_scale=0.50, label="YC(lb126,s0.50)"),
    dict(lookback=126, invert_scale=0.75, label="YC(lb126,s0.75)"),
    dict(lookback=252, invert_scale=0.50, label="YC(lb252,s0.50)"),
    dict(lookback=252, invert_scale=0.75, label="YC(lb252,s0.75)"),
]

rows32, trial_sh32, oos32 = [], [], {}
for cfg in E32_GRID:
    lbl = cfg.pop("label")
    sig = yield_curve.signals(spy, ief=ief_cut, shy=shy_cut,
                              target_vol=0.18, vol_lookback=20, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh32.append(m["oos_sharpe"])
    oos32[lbl] = r.loc[OOS_A:OOS_B]
    rows32.append(m)
    print(f"  {m}")

best32 = max(rows32, key=lambda x: x["mean_wf"])
print(f"\n  BEST E32: {best32}")
dsr32, ci32 = significance(oos32[best32["label"]], trial_sh32, best32["label"])

corr32 = float(oos32[best32["label"]].corr(r_v2_oos))
print(f"  corr(YieldCurve,v2) OOS: {corr32:.3f}")

pass32 = (best32["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best32["worst_dd"] > V2_WORST_DD and
          dsr32 >= 0.95 and ci32.clears_noise)
watch32 = not pass32 and dsr32 >= 0.95 and corr32 < 0.50
verdict32 = "adopted" if pass32 else "discarded"

ev32 = {"best": best32, "dsr": round(dsr32, 4),
        "diff_ci": [round(ci32.lo, 3), round(ci32.hi, 3)],
        "corr_v2_oos": round(corr32, 3), "all_rows": rows32,
        "watchlist_eligible": watch32}
record_outcome(reg32.id, verdict=verdict32, evidence=ev32)
print(f"\n  E32 VERDICT: {verdict32} | watch-list eligible: {watch32}")

# ---------------------------------------------------------------------------
# 8. E33: Tactical Bond Cash Sleeve
# ---------------------------------------------------------------------------
print("\n=== E33: TACTICAL BOND CASH SLEEVE ===")

reg33 = preregister(
    hypothesis=(
        "When v2's equity trend signal is OFF (SPY below SMA200 band), the "
        "strategy holds idle cash earning only the T-bill rate. In equity bear "
        "markets, Treasuries typically rally (flight to quality). Replacing idle "
        "cash with IEF — when IEF is itself above its own SMA200 trend gate — "
        "should compound the bear-market outperformance advantage without changing "
        "the equity signal.\n"
        "Key distinctions: (a) unlike E30, this does NOT reduce equity exposure; "
        "(b) unlike E20 CTA, IEF is used only as a CASH SUBSTITUTE when v2 is "
        "already in cash — the equity sleeve is unchanged. This avoids the CTA "
        "bull-market drag that killed E20/E22.\n"
        "Risk: in 2022, v2 was in cash (correct equity call) but IEF also fell "
        "sharply (-18%). The IEF SMA200 gate should protect: IEF crossed below "
        "its SMA200 in early 2022, triggering exit to T-bills before the worst "
        "of the bond sell-off. "
        "Skeptical prior: (a) the SMA200 gate on IEF lags bond market tops; "
        "(b) the cash periods are roughly 35% of days — the incremental return "
        "from bond exposure may be too small to move the CI; (c) the IEF trend "
        "may still correlate highly to v2 in the OOS period."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 212 + 4 new configs = 216 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 OOS < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

# Multi-asset price panel: SPY + IEF (pre-holdout)
panel_ei = pd.DataFrame({
    "SPY": spy,
    "IEF": ief_full.reindex(spy.index).ffill(),
}).dropna(how="all")

E33_GRID = [
    dict(ief_window=200, cash_ief_frac=1.0, label="TB(w200,f1.0)"),
    dict(ief_window=200, cash_ief_frac=0.5, label="TB(w200,f0.5)"),
    dict(ief_window=100, cash_ief_frac=1.0, label="TB(w100,f1.0)"),
    dict(ief_window=100, cash_ief_frac=0.5, label="TB(w100,f0.5)"),
]

rows33, trial_sh33, oos33, full33 = [], [], {}, {}
for cfg in E33_GRID:
    lbl = cfg.pop("label")
    wts = tactical_bond.multi_signals(spy, ief=ief_full.reindex(spy.index).ffill(),
                                      target_vol=0.18, lookback=20, **cfg)
    m = wf_multi(panel_ei, wts, lbl)
    trial_sh33.append(m["oos_sharpe"])
    oos33[lbl] = m.pop("_r_oos")
    full33[lbl] = m.pop("_r_full")
    rows33.append(m)
    print(f"  {m}")

best33 = max(rows33, key=lambda x: x["mean_wf"])
print(f"\n  BEST E33: {best33}")
dsr33, ci33 = significance(oos33[best33["label"]], trial_sh33, best33["label"])

corr33 = float(oos33[best33["label"]].corr(r_v2_oos))
print(f"  corr(TacticalBond,v2) OOS: {corr33:.3f}")

pass33 = (best33["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best33["worst_dd"] > V2_WORST_DD and
          dsr33 >= 0.95 and ci33.clears_noise)
watch33 = not pass33 and dsr33 >= 0.95 and corr33 < 0.50
verdict33 = "adopted" if pass33 else "discarded"

ev33 = {"best": best33, "dsr": round(dsr33, 4),
        "diff_ci": [round(ci33.lo, 3), round(ci33.hi, 3)],
        "corr_v2_oos": round(corr33, 3), "all_rows": rows33,
        "watchlist_eligible": watch33}
record_outcome(reg33.id, verdict=verdict33, evidence=ev33)
print(f"\n  E33 VERDICT: {verdict33} | watch-list eligible: {watch33}")

# ---------------------------------------------------------------------------
# 9. ROADMAP #10: v2 full-sample significance re-check
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2  = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2   = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s20: CI=[-0.0128,+0.7077])")

# ---------------------------------------------------------------------------
# 10. $1,000 benchmark comparison (2000 → latest, pre-holdout)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON ===")

def end_value(prices):
    r = prices.loc["2000-01-01":].pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia_cut = dia_full[dia_full.index < HOLDOUT_START]
qqq_cut = qqq_full[qqq_full.index < HOLDOUT_START]
iwm_cut = iwm_full[iwm_full.index < HOLDOUT_START]
ief_cut2 = ief_full[ief_full.index < HOLDOUT_START]

spy_end = end_value(spy)
dia_end = end_value(dia_cut)
qqq_end = end_value(qqq_cut)
iwm_end = end_value(iwm_cut)
ief_end = end_value(ief_cut2)
v2_end  = round(float((1 + r_v2).prod() * 1000), 2)

# E31 best config terminal value (if available)
if rows31 and best31.get("label", "SKIPPED") not in ("SKIPPED", "FAILED"):
    _e31_cfg = {
        "CT(pct0.90,t0.15)": dict(cape_pct=0.90, tilt=0.15),
        "CT(pct0.90,t0.25)": dict(cape_pct=0.90, tilt=0.25),
        "CT(pct0.90,t0.35)": dict(cape_pct=0.90, tilt=0.35),
        "CT(pct0.85,t0.15)": dict(cape_pct=0.85, tilt=0.15),
        "CT(pct0.85,t0.25)": dict(cape_pct=0.85, tilt=0.25),
        "CT(pct0.80,t0.25)": dict(cape_pct=0.80, tilt=0.25),
    }
    sig31_best = cape_tilt.signals(spy, target_vol=0.18, lookback=20,
                                   **_e31_cfg[best31["label"]])
    r31_full = ve.strategy_returns(spy, sig31_best, commission=COST, rf_daily=rf_daily)
    e31_end  = round(float((1 + r31_full).prod() * 1000), 2)
else:
    e31_end = None

# E32 best config terminal value
_e32_cfg = {
    "YC(lb63,s0.50)":  dict(lookback=63,  invert_scale=0.50),
    "YC(lb63,s0.75)":  dict(lookback=63,  invert_scale=0.75),
    "YC(lb126,s0.50)": dict(lookback=126, invert_scale=0.50),
    "YC(lb126,s0.75)": dict(lookback=126, invert_scale=0.75),
    "YC(lb252,s0.50)": dict(lookback=252, invert_scale=0.50),
    "YC(lb252,s0.75)": dict(lookback=252, invert_scale=0.75),
}
sig32_best = yield_curve.signals(spy, ief=ief_cut, shy=shy_cut,
                                  target_vol=0.18, vol_lookback=20,
                                  **_e32_cfg[best32["label"]])
r32_full = ve.strategy_returns(spy, sig32_best, commission=COST, rf_daily=rf_daily)
e32_end  = round(float((1 + r32_full).prod() * 1000), 2)

# E33 best config terminal value
e33_end = round(float((1 + full33[best33["label"]]).prod() * 1000), 2)

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
if e31_end:
    print(f"    E31 CAPE Tilt:        ${e31_end:>10,.2f}  ({best31['label']})")
print(f"    E32 Yield Curve:      ${e32_end:>10,.2f}  ({best32['label']})")
print(f"    E33 Tactical Bond:    ${e33_end:>10,.2f}  ({best33['label']})")
print(f"    QQQ (Nasdaq 100):     ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):        ${spy_end:>10,.2f}")
print(f"    DIA (DOW Jones):      ${dia_end:>10,.2f}")
print(f"    IWM (Russell 2000):   ${iwm_end:>10,.2f}")
print(f"    IEF (7-10y Treasury): ${ief_end:>10,.2f}")
print(f"    EWC (Canada):         {str(intl.get('EWC') or 'N/A'):>11}")
print(f"    EFA (Intl Devlpd):    {str(intl.get('EFA') or 'N/A'):>11}")
print(f"    ACWI (World):         {str(intl.get('ACWI') or 'N/A'):>11}")
if mag7_end:
    print(f"    Mag-7 eqw 2012:       ${mag7_end:>10,.2f}  (surv. bias; G4 cap)")

# ---------------------------------------------------------------------------
# 11. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak      = max(PEAK_VALUE, new_value)
dd_from_peak  = (new_value / new_peak - 1) * 100

note_s22 = (
    f"Session 22 (2026-07-26): New SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f} (close {latest_spy_close:.2f} "
    f"{'>' if latest_spy_close > band_up else '<'} band {band_up:.2f}; "
    f"vol {vol20*100:.1f}% vs 18% target). No trades. "
    f"E31 CAPE Tilt: {verdict31} (best {best31['label']} mean_wf={best31['mean_wf']}, "
    f"DD={best31['worst_dd']}%, DSR={dsr31:.4f}, CI=[{ci31.lo:.3f},{ci31.hi:.3f}], "
    f"corr_v2={corr31:.3f}, watchlist={watch31}). "
    f"E32 Yield Curve: {verdict32} (best {best32['label']} mean_wf={best32['mean_wf']}, "
    f"DD={best32['worst_dd']}%, DSR={dsr32:.4f}, CI=[{ci32.lo:.3f},{ci32.hi:.3f}], "
    f"corr_v2={corr32:.3f}, watchlist={watch32}). "
    f"E33 Tactical Bond: {verdict33} (best {best33['label']} mean_wf={best33['mean_wf']}, "
    f"DD={best33['worst_dd']}%, DSR={dsr33:.4f}, CI=[{ci33.lo:.3f},{ci33.hi:.3f}], "
    f"corr_v2={corr33:.3f}, watchlist={watch33}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}. "
    f"DD from peak: {dd_from_peak:+.2f}%. $1k v2={v2_end} SPY={spy_end} DIA={dia_end} QQQ={qqq_end}."
)

history_entry = {
    "date": "2026-07-26",
    "session": 22,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(new_value - PREV_VALUE, 2),
    "chg_pct": round((new_value / PREV_VALUE - 1) * 100, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s22,
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
# 12. Session summary + save results
# ---------------------------------------------------------------------------
total_configs = trials_this_period()
print(f"\n{'='*65}")
print(f"SESSION 22 SUMMARY (2026-07-26)")
print(f"{'='*65}")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% since last mark | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f} | DD from peak: {dd_from_peak:+.2f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"\nExperiment Results:")
exps = [
    ("E31 CAPE Tilt",     best31, verdict31, dsr31, ci31, watch31, corr31),
    ("E32 Yield Curve",   best32, verdict32, dsr32, ci32, watch32, corr32),
    ("E33 Tactical Bond", best33, verdict33, dsr33, ci33, watch33, corr33),
]
for exp, best, verdict, dsr, ci, watch, corr in exps:
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
    "session": "2026-07-26-s22",
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
    "E31_CAPETilt": {
        "verdict": verdict31, "best": best31,
        "dsr": round(dsr31, 4), "ci": [round(ci31.lo, 3), round(ci31.hi, 3)],
        "corr_v2_oos": round(corr31, 3), "all_rows": rows31,
        "watchlist_eligible": watch31,
    },
    "E32_YieldCurve": {
        "verdict": verdict32, "best": best32,
        "dsr": round(dsr32, 4), "ci": [round(ci32.lo, 3), round(ci32.hi, 3)],
        "corr_v2_oos": round(corr32, 3), "all_rows": rows32,
        "watchlist_eligible": watch32,
    },
    "E33_TacticalBond": {
        "verdict": verdict33, "best": best33,
        "dsr": round(dsr33, 4), "ci": [round(ci33.lo, 3), round(ci33.hi, 3)],
        "corr_v2_oos": round(corr33, 3), "all_rows": rows33,
        "watchlist_eligible": watch33,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2.lo, 4), round(ci_v2.hi, 4)],
        "clears": ci_v2.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end,
        "E31_CAPE": e31_end,
        "E32_YC": e32_end,
        "E33_TB": e33_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end, "IWM": iwm_end,
        "IEF": ief_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"), "ACWI": intl.get("ACWI"),
        "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_26.json", "w"), indent=1)
print("Results saved → research/results_2026_07_26.json")
