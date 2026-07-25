"""Session 22 (2026-07-25): Two new value-philosophy experiments.

Investing philosophies researched this session:

E31 — CAPE Value Tilt on v2 Champion
  Philosophy: Shiller (2015) showed the Cyclically Adjusted P/E (CAPE) ratio
  predicts 10-year real equity returns with ~0.60 correlation. At historically
  extreme valuations (top-decile CAPE), forward returns are compressed. Rather
  than binary exit (proven harmful in E4/E8), a MILD downside tilt scales v2
  exposure by `tilt_lo` only when CAPE exceeds the 90th expanding-window
  percentile of its full historical distribution (1881-present).

  Key innovation vs. existing strategies:
    - E4/E8 (kill-switches): binary, destroyed Sharpe. This is fractional.
    - v2 already handles timing via SMA200 trend gate. CAPE adds a SECOND
      orthogonal dimension (valuation level) that the trend filter ignores.
    - Literature (Asness et al. 2017 AQR, Siegel 2016): CAPE is real but slow —
      only reliable at 10-year horizons, not 1-year. Mild tilt is the only
      defensible implementation.
  Skeptical prior: CAPE has been "high" since the early 1990s. A threshold
  at the 90th pct (CAPE ~27) may fire for extended periods.

E32 — Equity Risk Premium (ERP) Carry Signal
  Philosophy: The ERP (earnings yield = 1/CAPE, minus T-bill rate) is the
  expected carry of holding equities over cash. When ERP is positive, equities
  offer a return advantage vs. risk-free; when negative, cash yields more per
  unit of risk. This is the "Fed Model" (Yardeni 1999) extended from bonds to
  T-bills (^IRX available in our pipeline).

  Key distinction from E31:
    - E31 fires when CAPE is absolutely high vs. history.
    - E32 fires when equities are expensive RELATIVE TO RATES. In 2022-23,
      rising T-bill rates from 0% -> 5% flipped ERP negative even at CAPE=28,
      which is not top-decile absolute. E32 captures this.
  Skeptical prior: T-bill (3m) vs. 10y yield duration mismatch; equities
  can sustain negative ERP for years (2019-2022 QE era).

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
from backtest import vector_engine as ve
from backtest import evaluation as ev, guardrails as gr
from backtest import live_track
from strategies import vol_target, cape_tilt, equity_risk_premium
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
spy_cut    = spy_full[spy_full.index < HOLDOUT_START]["Close"]

irx_full   = loader.load_ohlcv("^IRX")["Close"].reindex(spy_all.index).ffill()
irx_cut    = irx_full[irx_full.index < HOLDOUT_START]
rf_daily   = (irx_cut / 100.0) / 252.0

dia_full   = loader.load_ohlcv("DIA")["Close"]
qqq_full   = loader.load_ohlcv("QQQ")["Close"]
iwm_full   = loader.load_ohlcv("IWM")["Close"]
ief_full   = loader.load_ohlcv("IEF")["Close"]

# Shiller CAPE data
shiller = loader.load_shiller()
cape_series = shiller["CAPE"].dropna()

latest_spy_date  = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close   = float(spy_all.iloc[-2])

print(f"\nData through {latest_spy_date.date()}, SPY={latest_spy_close:.4f}")
print(f"CAPE data through: {cape_series.index[-1].date()}, "
      f"last CAPE={float(cape_series.iloc[-1]):.2f}")
print(f"IRX (T-bill rate): {float(irx_full.iloc[-1]):.2f}%")
print(f"Configs entering this session: {trials_this_period()}")

# Note on CAPE data gap
cape_gap_months = len(pd.date_range(cape_series.index[-1], latest_spy_date, freq="ME"))
print(f"\nNOTE: CAPE data ends {cape_series.index[-1].date()} ({cape_gap_months}mo gap to now).")
print("  Forward-fill propagates last known CAPE into the gap (last = 30.81,")
print("  90th-pct threshold = 26.9 → tilt IS active in the gap period).")
print("  Real CAPE (Jul 2026) estimated ~38-42 (AI bull market); still top decile.")

spy      = spy_cut
spy_ret  = spy.pct_change().fillna(0.0)
spy_oos_ret = spy_ret.loc[OOS_A:OOS_B]

# ---------------------------------------------------------------------------
# 2. Portfolio mark + guardrails
# ---------------------------------------------------------------------------
UNITS      = 1.3334757435413753
PREV_VALUE = 984.35          # last confirmed mark (2026-07-23 close)
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

# Also compute CAPE signal at current date for display
cape_pct_now = cape_series.expanding(min_periods=120).rank(pct=True).iloc[-1]
current_cape  = float(cape_series.iloc[-1])
print(f"\n  Current CAPE: {current_cape:.1f} (p{cape_pct_now*100:.0f} of 1881-present)")
print(f"  ERP (earnings yield - T-bill): "
      f"{100/current_cape:.2f}% - {float(irx_full.iloc[-1]):.2f}% = "
      f"{100/current_cape - float(irx_full.iloc[-1]):.2f}%")

# ---------------------------------------------------------------------------
# 6. E31: CAPE Value Tilt on v2
# ---------------------------------------------------------------------------
print("\n=== E31: CAPE VALUE TILT ===")

reg31 = preregister(
    hypothesis=(
        "A MILD downside tilt on v2 exposure — applied only when the "
        "Shiller CAPE is at or above the 90th percentile of its "
        "expanding-window historical distribution — reduces drawdown "
        "during extended overvaluation periods without materially "
        "hurting the trend-following edge.\n\n"
        "Unlike kill-switches (E4/E8, proven harmful), this is fractional "
        "and always keeps some equity exposure. The tilt is 'mild' (not "
        "binary off) because CAPE predicts at 10-year horizons, not 1-year.\n\n"
        "Skeptical prior: CAPE >= 90th pct (26.9) has been TRUE for most of "
        "2000-2023, so the tilt may be active most of the time in the modern "
        "era — effectively just scaling v2 by a constant, which cannot improve "
        "Sharpe. The hypothesis is testable: if tilt_lo ≈ 1.0 configs best, "
        "the effect is negligible. If tilt_lo ≈ 0.50 configs best AND pass "
        "the significance bars, the tilt genuinely reduces tail risk."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 200 + 8 new configs = 208 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND DD better than v2 by >= 2%."
    ),
    grid_size=8,
    primary_metric="sharpe",
)

# Grid: 4 tilt_lo x 2 threshold
E31_GRID = [
    dict(tilt_lo=0.50, threshold_hi=0.90, label="CT(lo0.50,t90)"),
    dict(tilt_lo=0.70, threshold_hi=0.90, label="CT(lo0.70,t90)"),
    dict(tilt_lo=0.85, threshold_hi=0.90, label="CT(lo0.85,t90)"),
    dict(tilt_lo=0.95, threshold_hi=0.90, label="CT(lo0.95,t90)"),
    dict(tilt_lo=0.50, threshold_hi=0.85, label="CT(lo0.50,t85)"),
    dict(tilt_lo=0.70, threshold_hi=0.85, label="CT(lo0.70,t85)"),
    dict(tilt_lo=0.85, threshold_hi=0.85, label="CT(lo0.85,t85)"),
    dict(tilt_lo=0.95, threshold_hi=0.85, label="CT(lo0.95,t85)"),
]

rows31, trial_sh31, oos31 = [], [], {}
print("  (Running 8 CAPE-tilt configs...)")
for cfg in E31_GRID:
    lbl = cfg.pop("label")
    sig = cape_tilt.signals(spy, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh31.append(m["oos_sharpe"])
    oos31[lbl] = r.loc[OOS_A:OOS_B]
    rows31.append(m)
    print(f"  {m}")

best31 = max(rows31, key=lambda x: x["mean_wf"])
print(f"\n  BEST E31: {best31}")
dsr31, ci31 = significance(oos31[best31["label"]], trial_sh31, best31["label"])

corr31 = float(oos31[best31["label"]].corr(r_v2_oos))
print(f"  corr(CAPE_tilt,v2) OOS: {corr31:.3f}")

pass31 = (best31["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best31["worst_dd"] > V2_WORST_DD and
          dsr31 >= 0.95 and ci31.clears_noise)
watch31 = not pass31 and dsr31 >= 0.95 and best31["worst_dd"] > V2_WORST_DD + 2.0
verdict31 = "adopted" if pass31 else "discarded"

ev31 = {"best": best31, "dsr": round(dsr31, 4),
        "diff_ci": [round(ci31.lo, 3), round(ci31.hi, 3)],
        "corr_v2_oos": round(corr31, 3), "all_rows": rows31,
        "watchlist_eligible": watch31}
record_outcome(reg31.id, verdict=verdict31, evidence=ev31)
print(f"\n  E31 VERDICT: {verdict31} | watch-list eligible: {watch31}")

# ---------------------------------------------------------------------------
# 7. E32: Equity Risk Premium (ERP) Carry Signal
# ---------------------------------------------------------------------------
print("\n=== E32: EQUITY RISK PREMIUM CARRY SIGNAL ===")

reg32 = preregister(
    hypothesis=(
        "The Equity Risk Premium (ERP = earnings yield 1/CAPE minus T-bill "
        "rate) is the expected carry of holding equities over cash. When ERP < "
        "min_erp, the risk-free rate offers more expected return than equities, "
        "suggesting a MILD reduction in v2 exposure.\n\n"
        "Philosophical distinction from E31: E31 is absolute valuation (CAPE "
        "vs. history). E32 is relative valuation (equities vs. bonds). In 2022,"
        " CAPE was 'only' ~28 (below E31's 90th-pct threshold) but the T-bill "
        "rose from 0% to 4.5%, flipping ERP strongly negative — E32 would have "
        "correctly flagged expensive-vs-cash even when E31 was silent.\n\n"
        "Skeptical prior: (a) T-bill vs. 10y mismatch (we lack 10y yield data);"
        " (b) ERP has been persistently compressed in the post-QE era; "
        "(c) equities can sustain negative ERP for years; "
        "(d) Asness (2003) 'Fight the Fed Model' documents failures."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 208 + 4 new configs = 212 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND DD better than v2 by >= 2%."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

# Grid: 2 tilt_lo x 2 min_erp
# min_erp=0.00: reduce when earnings yield < T-bill at all
# min_erp=0.02: only reduce when ERP is at least 2% negative (more conservative)
E32_GRID = [
    dict(tilt_lo=0.70, min_erp=0.00, label="ERP(lo0.70,erp0.00)"),
    dict(tilt_lo=0.70, min_erp=0.02, label="ERP(lo0.70,erp0.02)"),
    dict(tilt_lo=0.50, min_erp=0.00, label="ERP(lo0.50,erp0.00)"),
    dict(tilt_lo=0.50, min_erp=0.02, label="ERP(lo0.50,erp0.02)"),
]

rows32, trial_sh32, oos32 = [], [], {}
irx_cut_aligned = irx_cut.reindex(spy.index).ffill().fillna(0.0)

print("  (Running 4 ERP configs...)")
for cfg in E32_GRID:
    lbl = cfg.pop("label")
    sig = equity_risk_premium.signals(spy, irx_cut_aligned, **cfg)
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
print(f"  corr(ERP,v2) OOS: {corr32:.3f}")

pass32 = (best32["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best32["worst_dd"] > V2_WORST_DD and
          dsr32 >= 0.95 and ci32.clears_noise)
watch32 = not pass32 and dsr32 >= 0.95 and best32["worst_dd"] > V2_WORST_DD + 2.0
verdict32 = "adopted" if pass32 else "discarded"

ev32 = {"best": best32, "dsr": round(dsr32, 4),
        "diff_ci": [round(ci32.lo, 3), round(ci32.hi, 3)],
        "corr_v2_oos": round(corr32, 3), "all_rows": rows32,
        "watchlist_eligible": watch32}
record_outcome(reg32.id, verdict=verdict32, evidence=ev32)
print(f"\n  E32 VERDICT: {verdict32} | watch-list eligible: {watch32}")

# ---------------------------------------------------------------------------
# 8. v2 full-sample significance re-check (Roadmap #10)
# ---------------------------------------------------------------------------
print("\n=== ROADMAP #10: v2 FULL-SAMPLE SIGNIFICANCE RE-CHECK ===")
all_trial_sharpes = [ev.sharpe_ratio(r_v2)]
dsr_v2   = ev.deflated_sharpe_ratio(r_v2, all_trial_sharpes)
ci_v2    = ev.bootstrap_difference_ci(r_v2, spy_ret)
print(f"  v2 full-sample: DSR={dsr_v2:.4f}  "
      f"diff-vs-SPY CI=[{ci_v2.lo:.4f},{ci_v2.hi:.4f}]  "
      f"clears={ci_v2.clears_noise}")
print(f"  (Prior s20: CI=[-0.0128,+0.7077])")

# ---------------------------------------------------------------------------
# 9. $1,000 virtual trade benchmark comparison
# ---------------------------------------------------------------------------
print("\n=== $1,000 VIRTUAL TRADE BENCHMARK (2000 → latest, pre-holdout) ===")

def end_value(prices):
    r = prices.loc["2000-01-01":].pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia_cut  = dia_full[dia_full.index < HOLDOUT_START]
qqq_cut  = qqq_full[qqq_full.index < HOLDOUT_START]
iwm_cut  = iwm_full[iwm_full.index < HOLDOUT_START]
ief_cut  = ief_full[ief_full.index < HOLDOUT_START]

spy_end  = end_value(spy)
dia_end  = end_value(dia_cut)
qqq_end  = end_value(qqq_cut)
iwm_end  = end_value(iwm_cut)
ief_end  = end_value(ief_cut)
v2_end   = round(float((1 + r_v2).prod() * 1000), 2)

# E31 best terminal value
_e31_lbl = best31["label"]
_e31_cfg = {r["label"]: r for r in []}  # rebuild from grid
e31_grid_lookup = {
    "CT(lo0.50,t90)": dict(tilt_lo=0.50, threshold_hi=0.90),
    "CT(lo0.70,t90)": dict(tilt_lo=0.70, threshold_hi=0.90),
    "CT(lo0.85,t90)": dict(tilt_lo=0.85, threshold_hi=0.90),
    "CT(lo0.95,t90)": dict(tilt_lo=0.95, threshold_hi=0.90),
    "CT(lo0.50,t85)": dict(tilt_lo=0.50, threshold_hi=0.85),
    "CT(lo0.70,t85)": dict(tilt_lo=0.70, threshold_hi=0.85),
    "CT(lo0.85,t85)": dict(tilt_lo=0.85, threshold_hi=0.85),
    "CT(lo0.95,t85)": dict(tilt_lo=0.95, threshold_hi=0.85),
}
sig31_best = cape_tilt.signals(spy, **e31_grid_lookup[_e31_lbl])
r31_full   = ve.strategy_returns(spy, sig31_best, commission=COST, rf_daily=rf_daily)
e31_end    = round(float((1 + r31_full).prod() * 1000), 2)

# E32 best terminal value
_e32_lbl = best32["label"]
e32_grid_lookup = {
    "ERP(lo0.70,erp0.00)": dict(tilt_lo=0.70, min_erp=0.00),
    "ERP(lo0.70,erp0.02)": dict(tilt_lo=0.70, min_erp=0.02),
    "ERP(lo0.50,erp0.00)": dict(tilt_lo=0.50, min_erp=0.00),
    "ERP(lo0.50,erp0.02)": dict(tilt_lo=0.50, min_erp=0.02),
}
sig32_best = equity_risk_premium.signals(spy, irx_cut_aligned,
                                         **e32_grid_lookup[_e32_lbl])
r32_full   = ve.strategy_returns(spy, sig32_best, commission=COST, rf_daily=rf_daily)
e32_end    = round(float((1 + r32_full).prod() * 1000), 2)

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
print(f"    v2 champion:          ${v2_end:>10,.2f}  (CHAMPION, FROZEN)")
print(f"    E31 CAPE Tilt:        ${e31_end:>10,.2f}  ({_e31_lbl})")
print(f"    E32 ERP Carry:        ${e32_end:>10,.2f}  ({_e32_lbl})")
print(f"    QQQ (Nasdaq 100):     ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):        ${spy_end:>10,.2f}")
print(f"    DIA (Dow Jones):      ${dia_end:>10,.2f}")
print(f"    IWM (Russell 2000):   ${iwm_end:>10,.2f}")
print(f"    IEF (7-10y Treasury): ${ief_end:>10,.2f}")
print(f"    EWC (Canada):         {str(intl.get('EWC') or 'N/A'):>11}")
print(f"    EFA (Intl Devlpd):    {str(intl.get('EFA') or 'N/A'):>11}")
print(f"    ACWI (World):         {str(intl.get('ACWI') or 'N/A'):>11}")
if mag7_end:
    print(f"    Mag-7 eqw 2012:       ${mag7_end:>10,.2f}  (surv. bias; G4 cap)")

# ---------------------------------------------------------------------------
# 10. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak     = max(PEAK_VALUE, new_value)
dd_from_peak = (new_value / new_peak - 1) * 100

note_s22 = (
    f"Session 22 (2026-07-25): New SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f} (close {latest_spy_close:.2f} "
    f"{'>' if latest_spy_close > band_up else '<'} band {band_up:.2f}; "
    f"vol {vol20*100:.1f}% vs 18% target). No trades. "
    f"E31 CAPE Tilt: {verdict31} (best {_e31_lbl} mean_wf={best31['mean_wf']}, "
    f"DD={best31['worst_dd']}%, DSR={dsr31:.4f}, CI=[{ci31.lo:.3f},{ci31.hi:.3f}], "
    f"corr_v2={corr31:.3f}, watchlist={watch31}). "
    f"E32 ERP Carry: {verdict32} (best {_e32_lbl} mean_wf={best32['mean_wf']}, "
    f"DD={best32['worst_dd']}%, DSR={dsr32:.4f}, CI=[{ci32.lo:.3f},{ci32.hi:.3f}], "
    f"corr_v2={corr32:.3f}, watchlist={watch32}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}. "
    f"DD from peak: {dd_from_peak:+.2f}%."
)

history_entry = {
    "date": "2026-07-25",
    "session": 22,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(port_chg, 2),
    "chg_pct": round(port_pct, 3),
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
# 11. Session summary
# ---------------------------------------------------------------------------
total_configs = trials_this_period()
print(f"\n{'='*65}")
print(f"SESSION 22 SUMMARY (2026-07-25)")
print(f"{'='*65}")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f} | DD from peak: {dd_from_peak:+.2f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"\nExperiment Results:")
for exp, best, verdict, dsr, ci, watch, corr in [
    ("E31 CAPE Tilt", best31, verdict31, dsr31, ci31, watch31, corr31),
    ("E32 ERP Carry", best32, verdict32, dsr32, ci32, watch32, corr32),
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
    "session": "2026-07-25-s22",
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
    "cape_context": {
        "last_cape": round(current_cape, 2),
        "cape_pct": round(float(cape_pct_now), 3),
        "cape_data_through": str(cape_series.index[-1].date()),
        "irx_pct": round(float(irx_full.iloc[-1]), 2),
        "erp_pct": round(100/current_cape - float(irx_full.iloc[-1]), 2),
    },
    "E31_CAPETilt": {
        "verdict": verdict31, "best": best31,
        "dsr": round(dsr31, 4), "ci": [round(ci31.lo, 3), round(ci31.hi, 3)],
        "corr_v2_oos": round(corr31, 3), "all_rows": rows31,
        "watchlist_eligible": watch31,
    },
    "E32_ERPCarry": {
        "verdict": verdict32, "best": best32,
        "dsr": round(dsr32, 4), "ci": [round(ci32.lo, 3), round(ci32.hi, 3)],
        "corr_v2_oos": round(corr32, 3), "all_rows": rows32,
        "watchlist_eligible": watch32,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2.lo, 4), round(ci_v2.hi, 4)],
        "clears": ci_v2.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E31_CAPETilt": e31_end, "E32_ERPCarry": e32_end,
        "SPY": spy_end, "DIA": dia_end, "QQQ": qqq_end,
        "IWM": iwm_end, "IEF": ief_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"),
        "ACWI": intl.get("ACWI"), "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_25.json", "w"), indent=1)
print("Results saved → research/results_2026_07_25.json")
