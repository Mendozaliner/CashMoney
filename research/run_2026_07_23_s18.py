"""Session 18 (2026-07-23): Three new investing-philosophy families.

Investing philosophies researched this session:

E26 — Donchian Channel Breakout (Turtle Trading)
  Richard Dennis & William Eckhardt (1983): pure mechanical breakout trend-
  following. Enter on N-day price high, exit on M-day price low. Fundamentally
  different from v2's SMA200 level comparison — this reacts to RANGE BREAKOUTS
  rather than lagged averages. Used by AQR, Graham Capital, Millburn.
  Two systems: S1(entry20/exit10) and S2(entry55/exit20).

E27 — 52-Week High Proximity Momentum (Behavioral Finance)
  George & Hwang (2004): investor anchoring to the 52-week high creates a
  momentum effect. When price approaches the 52-week high, formerly hesitant
  buyers enter, propelling further gains. Signal: close/52wk_max ratio.
  Distinct from v2: uses "proximity to peak" rather than "level vs. average."
  Philosophy: markets are not fully efficient; cognitive anchoring persists.

E28 — ADX Trend Strength Filter (Wilder 1978)
  Average Directional Index measures trend STRENGTH (not direction). Key
  insight: v2's whipsaws occur most in low-ADX (choppy/directionless) regimes.
  Adding an ADX gate should reduce false-trend entry costs while keeping
  exposure during strong trends. v2 direction + ADX quality filter combo.
  Never attempted in this system (all prior experiments used direction-only).

Data through 2026-07-22 (fresh). Today: 2026-07-23.
Champion configs entering this session: 180.
"""
import sys, json, pathlib
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from data import loader
from backtest import vector_engine as ve, evaluation as ev, guardrails as gr
from strategies import vol_target, sma_trend
from strategies import donchian_trend as dct
from strategies import fiftytwo_week as fw
from strategies import adx_trend as adx_mod
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

spy_full = loader.load_ohlcv("SPY")
spy_full_cut = spy_full[spy_full.index < HOLDOUT_START]["Close"]
spy_all = spy_full["Close"]

ief_full = loader.load_ohlcv("IEF")["Close"]
gld_full = loader.load_ohlcv("GLD")["Close"]
dia_full = loader.load_ohlcv("DIA")["Close"]
qqq_full = loader.load_ohlcv("QQQ")["Close"]
iwm_full = loader.load_ohlcv("IWM")["Close"]

latest_spy_date  = spy_all.index[-1]
latest_spy_close = float(spy_all.iloc[-1])
prev_spy_close   = float(spy_all.iloc[-2])

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
UNITS      = 1.3334757435413753
PREV_VALUE = 997.81          # last confirmed mark (2026-07-21 close)
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
print(f"  v2 exposure: {current_sig:.4f}  (no rebalance needed; at 1.0)")

guardrail_result = gr.run_all(
    portfolio, spy_returns=spy_ret, stale_days=stale, peak_value=PEAK_VALUE
)
print(f"\n=== GUARDRAILS ===")
for c in guardrail_result["checks"]:
    status = "GREEN" if c["ok"] else "!! NON-GREEN !!"
    print(f"  {c['guardrail']}: {status}  {c.get('detail','')}{c.get('level','')}")

# ---------------------------------------------------------------------------
# 3. Walk-forward helper
# ---------------------------------------------------------------------------
def wf_single(series: pd.Series, label: str) -> dict:
    """Walk-forward metrics for a strategy-returns series."""
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
# 4. Baselines
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

# Precompute SPY OHLCV for ADX (needs H/L)
spy_ohlcv = spy_full[spy_full.index < HOLDOUT_START]

# ---------------------------------------------------------------------------
# 5. E26: Donchian Channel Breakout (Turtle Trading)
# ---------------------------------------------------------------------------
print("\n=== E26: DONCHIAN CHANNEL BREAKOUT (TURTLE TRADING) ===")

reg26 = preregister(
    hypothesis=(
        "Donchian channel breakout trend-following (Dennis & Eckhardt 1983 "
        "'Turtle Trading'), combined with volatility targeting, outperforms v2 "
        "in walk-forward testing by catching trend beginnings via RANGE "
        "BREAKOUTS rather than lagging moving-average levels. "
        "Skeptical prior: (a) entry on new highs is a well-known and heavily "
        "mined signal — out-of-sample edge likely decayed post-publication; "
        "(b) with daily rebalancing, the entry-on-N-day-high is close to a "
        "trend signal and may be highly correlated with SMA200; (c) single-asset "
        "SPY Donchian may whipsaw in sideways markets similarly to SMA crossovers."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 (v2 bar) AND worst-fold MaxDD better than "
        "-20.5% AND DSR >= 0.95 (against 180 + 4 new configs = 184 total) AND "
        "diff-vs-SPY bootstrap CI lower bound > 0. "
        "Secondary (watch-list): DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

E26_GRID = [
    dict(entry_window=20, exit_window=10, target_vol=0.18, label="DCH(S1,tv0.18)"),
    dict(entry_window=55, exit_window=20, target_vol=0.18, label="DCH(S2,tv0.18)"),
    dict(entry_window=20, exit_window=10, target_vol=0.15, label="DCH(S1,tv0.15)"),
    dict(entry_window=40, exit_window=15, target_vol=0.18, label="DCH(S3,tv0.18)"),
]

rows26, trial_sh26, oos26 = [], [], {}
for cfg in E26_GRID:
    lbl = cfg.pop("label")
    sig = dct.signals(spy, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh26.append(m["oos_sharpe"])
    oos26[lbl] = r.loc[OOS_A:OOS_B]
    rows26.append(m)
    print(f"  {m}")

best26 = max(rows26, key=lambda x: x["mean_wf"])
print(f"\n  BEST E26: {best26}")
dsr26, ci26 = significance(oos26[best26["label"]], trial_sh26, best26["label"])

corr26 = float(oos26[best26["label"]].corr(r_v2_oos))
print(f"  corr(Donchian,v2) OOS: {corr26:.3f}")

pass26 = (best26["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best26["worst_dd"] > V2_WORST_DD and
          dsr26 >= 0.95 and ci26.clears_noise)
watch26 = not pass26 and dsr26 >= 0.95 and corr26 < 0.50
verdict26 = "adopted" if pass26 else "discarded"

ev26 = {"best": best26, "dsr": round(dsr26, 4),
        "diff_ci": [round(ci26.lo, 3), round(ci26.hi, 3)],
        "corr_v2_oos": round(corr26, 3), "all_rows": rows26,
        "watchlist_eligible": watch26}
record_outcome(reg26.id, verdict=verdict26, evidence=ev26)
print(f"\n  E26 VERDICT: {verdict26} | watch-list eligible: {watch26}")

# ---------------------------------------------------------------------------
# 6. E27: 52-Week High Proximity Momentum (Behavioral Finance)
# ---------------------------------------------------------------------------
print("\n=== E27: 52-WEEK HIGH PROXIMITY MOMENTUM (GEORGE & HWANG 2004) ===")

reg27 = preregister(
    hypothesis=(
        "The 52-week high anchoring effect (George & Hwang 2004): investors "
        "anchor to the 52-week high as a reference price. When SPY is near its "
        "52-week high, delayed institutional buyers finally act, propelling "
        "further gains. A signal based on (close / 52wk_max) ratio, combined "
        "with vol targeting, outperforms v2 by capturing investor anchoring "
        "dynamics that a moving-average signal misses. "
        "Skeptical prior: (a) the original paper studied individual stocks, "
        "not broad market indices — the anchoring effect may not aggregate; "
        "(b) at the index level, proximity to 52-week high and SMA200 are "
        "correlated (indices near highs are also above their 200d average); "
        "(c) the threshold choice is parameter-sensitive and may overfit."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 AND worst-fold MaxDD better than -20.5% AND "
        "DSR >= 0.95 (against 184 + 4 = 188 total) AND diff-vs-SPY CI lower "
        "bound > 0. Secondary: DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

E27_GRID = [
    dict(thresh_high=0.90, thresh_low=0.80, target_vol=0.18,
         label="52wk(H0.90,L0.80,tv0.18)"),
    dict(thresh_high=0.95, thresh_low=0.85, target_vol=0.18,
         label="52wk(H0.95,L0.85,tv0.18)"),
    dict(thresh_high=0.85, thresh_low=0.75, target_vol=0.18,
         label="52wk(H0.85,L0.75,tv0.18)"),
    dict(thresh_high=0.90, thresh_low=0.80, target_vol=0.15,
         label="52wk(H0.90,L0.80,tv0.15)"),
]

rows27, trial_sh27, oos27 = [], [], {}
for cfg in E27_GRID:
    lbl = cfg.pop("label")
    sig = fw.signals(spy, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh27.append(m["oos_sharpe"])
    oos27[lbl] = r.loc[OOS_A:OOS_B]
    rows27.append(m)
    print(f"  {m}")

best27 = max(rows27, key=lambda x: x["mean_wf"])
print(f"\n  BEST E27: {best27}")
dsr27, ci27 = significance(oos27[best27["label"]], trial_sh27, best27["label"])

corr27 = float(oos27[best27["label"]].corr(r_v2_oos))
print(f"  corr(52wk,v2) OOS: {corr27:.3f}")

pass27 = (best27["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best27["worst_dd"] > V2_WORST_DD and
          dsr27 >= 0.95 and ci27.clears_noise)
watch27 = not pass27 and dsr27 >= 0.95 and corr27 < 0.50
verdict27 = "adopted" if pass27 else "discarded"

ev27 = {"best": best27, "dsr": round(dsr27, 4),
        "diff_ci": [round(ci27.lo, 3), round(ci27.hi, 3)],
        "corr_v2_oos": round(corr27, 3), "all_rows": rows27,
        "watchlist_eligible": watch27}
record_outcome(reg27.id, verdict=verdict27, evidence=ev27)
print(f"\n  E27 VERDICT: {verdict27} | watch-list eligible: {watch27}")

# ---------------------------------------------------------------------------
# 7. E28: ADX Trend Strength Filter (Wilder 1978)
# ---------------------------------------------------------------------------
print("\n=== E28: ADX TREND STRENGTH FILTER (WILDER 1978) ===")

reg28 = preregister(
    hypothesis=(
        "Wilder's (1978) ADX measures trend STRENGTH independent of direction. "
        "Adding an ADX gate on top of v2's SMA200/vol-target signal reduces "
        "whipsaw costs in low-ADX (choppy/ranging) market regimes while "
        "maintaining exposure during high-ADX (strong-trend) periods. This "
        "targets v2's known weakness: the occasional false-trend entry during "
        "low-conviction sideways markets, especially around SMA200 band edges. "
        "Skeptical prior: (a) ADX is computed from daily bars and may lag trend "
        "changes just as much as SMA200; (b) requiring both SMA200 AND ADX "
        "filter may over-restrict entry and reduce too much of the invested time; "
        "(c) ADX threshold is a free parameter prone to data snooping."
    ),
    success_criteria=(
        "mean WF Sharpe >= 0.844 AND worst-fold MaxDD better than -20.5% AND "
        "DSR >= 0.95 (against 188 + 4 = 192 total configs) AND diff-vs-SPY CI "
        "lower bound > 0. Secondary: DSR >= 0.95 AND corr to v2 < 0.50."
    ),
    grid_size=4,
    primary_metric="sharpe",
)

spy_high = spy_ohlcv["High"] if "High" in spy_ohlcv.columns else None
spy_low  = spy_ohlcv["Low"]  if "Low"  in spy_ohlcv.columns else None

E28_GRID = [
    dict(adx_period=14, adx_threshold=20, target_vol=0.18,
         label="ADX(p14,t20,tv0.18)"),
    dict(adx_period=14, adx_threshold=25, target_vol=0.18,
         label="ADX(p14,t25,tv0.18)"),
    dict(adx_period=20, adx_threshold=20, target_vol=0.18,
         label="ADX(p20,t20,tv0.18)"),
    dict(adx_period=20, adx_threshold=25, target_vol=0.18,
         label="ADX(p20,t25,tv0.18)"),
]

rows28, trial_sh28, oos28 = [], [], {}
for cfg in E28_GRID:
    lbl = cfg.pop("label")
    sig = adx_mod.signals(spy, high=spy_high, low=spy_low, **cfg)
    r   = ve.strategy_returns(spy, sig, commission=COST, rf_daily=rf_daily)
    m   = wf_single(r, lbl)
    trial_sh28.append(m["oos_sharpe"])
    oos28[lbl] = r.loc[OOS_A:OOS_B]
    rows28.append(m)
    print(f"  {m}")

best28 = max(rows28, key=lambda x: x["mean_wf"])
print(f"\n  BEST E28: {best28}")
dsr28, ci28 = significance(oos28[best28["label"]], trial_sh28, best28["label"])

corr28 = float(oos28[best28["label"]].corr(r_v2_oos))
print(f"  corr(ADX,v2) OOS: {corr28:.3f}")

pass28 = (best28["mean_wf"] >= V2_MEAN_WF_SHARPE and
          best28["worst_dd"] > V2_WORST_DD and
          dsr28 >= 0.95 and ci28.clears_noise)
watch28 = not pass28 and dsr28 >= 0.95 and corr28 < 0.50
verdict28 = "adopted" if pass28 else "discarded"

ev28 = {"best": best28, "dsr": round(dsr28, 4),
        "diff_ci": [round(ci28.lo, 3), round(ci28.hi, 3)],
        "corr_v2_oos": round(corr28, 3), "all_rows": rows28,
        "watchlist_eligible": watch28}
record_outcome(reg28.id, verdict=verdict28, evidence=ev28)
print(f"\n  E28 VERDICT: {verdict28} | watch-list eligible: {watch28}")

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
print(f"  (Prior: CI=[-0.0129,+0.7077] from s13; more live data now)")

# ---------------------------------------------------------------------------
# 9. $1,000 benchmark comparison (2000 → latest, pre-holdout)
# ---------------------------------------------------------------------------
print("\n=== $1,000 BENCHMARK COMPARISON ===")

def end_value(prices):
    r = prices.loc["2000-01-01":].pct_change().fillna(0.0)
    return round(float((1 + r).prod() * 1000), 2)

dia_cut = dia_full[dia_full.index < HOLDOUT_START]
qqq_cut = qqq_full[qqq_full.index < HOLDOUT_START]
iwm_cut = iwm_full[iwm_full.index < HOLDOUT_START]

spy_end  = end_value(spy)
dia_end  = end_value(dia_cut)
qqq_end  = end_value(qqq_cut)
iwm_end  = end_value(iwm_cut)
v2_end   = round(float((1 + r_v2).prod() * 1000), 2)

# Labels captured from the best row dictionaries
_e26_lbl = best26["label"]
_e27_lbl = best27["label"]
_e28_lbl = best28["label"]

# Config lookup tables (no mutation of the grid lists needed)
_e26_cfg = {
    "DCH(S1,tv0.18)": dict(entry_window=20, exit_window=10, target_vol=0.18),
    "DCH(S2,tv0.18)": dict(entry_window=55, exit_window=20, target_vol=0.18),
    "DCH(S1,tv0.15)": dict(entry_window=20, exit_window=10, target_vol=0.15),
    "DCH(S3,tv0.18)": dict(entry_window=40, exit_window=15, target_vol=0.18),
}
_e27_cfg = {
    "52wk(H0.90,L0.80,tv0.18)": dict(thresh_high=0.90, thresh_low=0.80, target_vol=0.18),
    "52wk(H0.95,L0.85,tv0.18)": dict(thresh_high=0.95, thresh_low=0.85, target_vol=0.18),
    "52wk(H0.85,L0.75,tv0.18)": dict(thresh_high=0.85, thresh_low=0.75, target_vol=0.18),
    "52wk(H0.90,L0.80,tv0.15)": dict(thresh_high=0.90, thresh_low=0.80, target_vol=0.15),
}
_e28_cfg = {
    "ADX(p14,t20,tv0.18)": dict(adx_period=14, adx_threshold=20, target_vol=0.18),
    "ADX(p14,t25,tv0.18)": dict(adx_period=14, adx_threshold=25, target_vol=0.18),
    "ADX(p20,t20,tv0.18)": dict(adx_period=20, adx_threshold=20, target_vol=0.18),
    "ADX(p20,t25,tv0.18)": dict(adx_period=20, adx_threshold=25, target_vol=0.18),
}

r_e26_best = ve.strategy_returns(
    spy, dct.signals(spy, **_e26_cfg[_e26_lbl]), COST, rf_daily)
r_e27_best = ve.strategy_returns(
    spy, fw.signals(spy, **_e27_cfg[_e27_lbl]), COST, rf_daily)
r_e28_best = ve.strategy_returns(
    spy, adx_mod.signals(spy, high=spy_high, low=spy_low, **_e28_cfg[_e28_lbl]),
    COST, rf_daily)

dch_end = round(float((1 + r_e26_best).prod() * 1000), 2)
fw_end  = round(float((1 + r_e27_best).prod() * 1000), 2)
adx_end = round(float((1 + r_e28_best).prod() * 1000), 2)

# Mag-7 (from 2012, survivorship-biased)
mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
try:
    mag7_panel = loader.load_universe(mag7, start="2012-05-18")
    mag7_panel = mag7_panel[mag7_panel.index < HOLDOUT_START].dropna()
    mag7_ret   = mag7_panel.pct_change().fillna(0.0).mean(axis=1)
    mag7_end   = round(float((1 + mag7_ret).prod() * 1000), 2)
except Exception:
    mag7_end   = None

# International (price-index, no dividends)
intl = {}
for t in ["EWC", "ACWI", "EFA", "EEM"]:
    try:
        p = loader.load_ohlcv(t)["Close"]
        p = p[p.index < HOLDOUT_START]
        intl[t] = end_value(p)
    except Exception:
        intl[t] = None

print(f"  $1k from 2000 → {latest_spy_date.date()} (pre-holdout):")
print(f"    v2 champion:    ${v2_end:>10,.2f}")
print(f"    E26 Donchian:   ${dch_end:>10,.2f}  ({_e26_lbl})")
print(f"    E27 52-wk Hi:   ${fw_end:>10,.2f}  ({_e27_lbl})")
print(f"    E28 ADX Filter: ${adx_end:>10,.2f}  ({_e28_lbl})")
print(f"    QQQ (Nasdaq):   ${qqq_end:>10,.2f}")
print(f"    SPY (S&P 500):  ${spy_end:>10,.2f}")
print(f"    DIA (DOW Jones):${dia_end:>10,.2f}")
print(f"    IWM (Russ 2k):  ${iwm_end:>10,.2f}")
print(f"    EWC (Canada):   ${intl.get('EWC') or 'N/A':>10}")
print(f"    EFA (Intl Devl):${intl.get('EFA') or 'N/A':>10}")
print(f"    ACWI (World):   ${intl.get('ACWI') or 'N/A':>10}")
if mag7_end:
    print(f"    Mag-7 eqw 2012: ${mag7_end:>10,.2f}  (survivorship bias; G4 cap)")

# ---------------------------------------------------------------------------
# 10. Update portfolio.json
# ---------------------------------------------------------------------------
new_peak     = max(PEAK_VALUE, new_value)
dd_from_peak = (new_value / new_peak - 1) * 100

note_s18 = (
    f"Session 18 (2026-07-23): New SPY close {latest_spy_close:.4f} "
    f"({latest_spy_date.date()}), {spy_day_chg:+.3f}% on the day. "
    f"{UNITS:.6f} units × ${latest_spy_close:.4f} = ${new_value:.2f} "
    f"({port_pct:+.3f}%). "
    f"v2 exposure {current_sig:.4f} (close {latest_spy_close:.2f} "
    f"{'>' if latest_spy_close > band_up else '<'} band {band_up:.2f}; "
    f"vol {vol20*100:.1f}% vs 18% target). No trades. "
    f"E26 Donchian: {verdict26} (best {_e26_lbl} mean_wf={best26['mean_wf']}, "
    f"DD={best26['worst_dd']}%, DSR={dsr26:.4f}, CI=[{ci26.lo:.3f},{ci26.hi:.3f}], "
    f"corr_v2={corr26:.3f}, watchlist={watch26}). "
    f"E27 52wk-High: {verdict27} (best {_e27_lbl} mean_wf={best27['mean_wf']}, "
    f"DD={best27['worst_dd']}%, DSR={dsr27:.4f}, CI=[{ci27.lo:.3f},{ci27.hi:.3f}], "
    f"corr_v2={corr27:.3f}, watchlist={watch27}). "
    f"E28 ADX Filter: {verdict28} (best {_e28_lbl} mean_wf={best28['mean_wf']}, "
    f"DD={best28['worst_dd']}%, DSR={dsr28:.4f}, CI=[{ci28.lo:.3f},{ci28.hi:.3f}], "
    f"corr_v2={corr28:.3f}, watchlist={watch28}). "
    f"Guardrails G1-G7 {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}. "
    f"DD from peak: {dd_from_peak:+.2f}%."
)

history_entry = {
    "date": "2026-07-23",
    "session": 18,
    "mark_date": str(latest_spy_date.date()),
    "value": new_value,
    "chg_dollar": round(port_chg, 2),
    "chg_pct": round(port_pct, 3),
    "spy_pct_same_window": round(spy_day_chg, 3),
    "all_time_pct": round(all_time_pct, 3),
    "note": note_s18,
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
# 11. Summary
# ---------------------------------------------------------------------------
total_configs = trials_this_period()
print(f"\n{'='*60}")
print(f"SESSION 18 SUMMARY (2026-07-23)")
print(f"{'='*60}")
print(f"Portfolio: ${new_value:.2f} ({port_pct:+.3f}% day | {all_time_pct:+.3f}% all-time)")
print(f"SPY since live baseline: {spy_since_live:+.3f}%")
print(f"v2 exposure: {current_sig:.4f} | DD from peak: {dd_from_peak:+.2f}%")
print(f"Guardrails: {'ALL GREEN' if guardrail_result['all_ok'] else 'NON-GREEN DETECTED'}")
print(f"\nExperiment Results:")
for exp, best, verdict, dsr, ci, watch, corr in [
    ("E26 Donchian", best26, verdict26, dsr26, ci26, watch26, corr26),
    ("E27 52wk Hi",  best27, verdict27, dsr27, ci27, watch27, corr27),
    ("E28 ADX",      best28, verdict28, dsr28, ci28, watch28, corr28),
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

# Save results
results = {
    "session": "2026-07-23-s18",
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
    "E26_Donchian": {
        "verdict": verdict26, "best": best26,
        "dsr": round(dsr26, 4), "ci": [round(ci26.lo, 3), round(ci26.hi, 3)],
        "corr_v2_oos": round(corr26, 3), "all_rows": rows26,
        "watchlist_eligible": watch26,
    },
    "E27_52wkHigh": {
        "verdict": verdict27, "best": best27,
        "dsr": round(dsr27, 4), "ci": [round(ci27.lo, 3), round(ci27.hi, 3)],
        "corr_v2_oos": round(corr27, 3), "all_rows": rows27,
        "watchlist_eligible": watch27,
    },
    "E28_ADX": {
        "verdict": verdict28, "best": best28,
        "dsr": round(dsr28, 4), "ci": [round(ci28.lo, 3), round(ci28.hi, 3)],
        "corr_v2_oos": round(corr28, 3), "all_rows": rows28,
        "watchlist_eligible": watch28,
    },
    "v2_significance": {
        "dsr": round(dsr_v2, 4),
        "diff_ci": [round(ci_v2.lo, 4), round(ci_v2.hi, 4)],
        "clears": ci_v2.clears_noise,
    },
    "benchmarks_1k": {
        "v2": v2_end, "E26_Donchian": dch_end, "E27_52wk": fw_end,
        "E28_ADX": adx_end, "SPY": spy_end, "DIA": dia_end,
        "QQQ": qqq_end, "IWM": iwm_end,
        "EWC": intl.get("EWC"), "EFA": intl.get("EFA"),
        "ACWI": intl.get("ACWI"), "Mag7_from2012": mag7_end,
    },
    "total_configs": total_configs,
}
json.dump(results, open("research/results_2026_07_23.json", "w"), indent=1)
print("Results saved → research/results_2026_07_23.json")
