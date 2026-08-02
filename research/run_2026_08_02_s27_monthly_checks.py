"""Session 27 monthly checks (2026-08-02):

1. v2 full-sample significance re-check (ROADMAP item #10, priority for
   first week of August): re-run the bootstrap CI vs SPY with updated
   data through 2026-07-31 (July complete).

2. Live-track July checkpoint (ROADMAP item #9): run monthly_checkpoints()
   to determine if July was a beat — first of 3 required months.

3. Portfolio mark at 2026-07-31 (already marked in s26, carried forward).

4. Kelly analysis of v2 champion (new tools/kelly.py).
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from data.loader import load_ohlcv, data_freshness
from backtest.vector_engine import strategy_returns
from strategies.vol_target import signals as v2_signals
from backtest.evaluation import bootstrap_difference_ci, sharpe_ratio
from backtest.live_track import summary as lt_summary
from backtest.guardrails import run_all as guardrails_run_all
from tools.kelly import kelly_summary, vol_target_to_kelly_equiv

COMMISSION = 0.0015

# ── Data ──────────────────────────────────────────────────────────────────
freshness = data_freshness()
print(f"Data freshness: {freshness}\n")

spy = load_ohlcv("SPY", "2000-01-01")["Close"]
irx = load_ohlcv("^IRX", "2000-01-01")["Close"] / 100 / 252
irx = irx.reindex(spy.index, method="ffill").fillna(0.0)
spy_ret = spy.pct_change().fillna(0.0)

# v2 champion
v2_sig = v2_signals(spy, target_vol=0.18, lookback=20)
v2_ret = strategy_returns(spy, v2_sig, commission=COMMISSION, rf_daily=irx)

# ── 1. Monthly significance re-check ──────────────────────────────────────
print("=" * 60)
print("CHECK #1: v2 Full-Sample Significance Re-check (August 2026)")
print("=" * 60)

ci = bootstrap_difference_ci(v2_ret.values, spy_ret.values,
                              metric="sharpe", n=10000, seed=42)
print(f"CI (v2 − SPY, full sample 2000→{spy.index[-1].date()}): "
      f"[{ci.lo:.4f}, {ci.hi:.4f}]")
print(f"Clears zero: {ci.clears_noise}")
print(f"Prior (s26):  [-0.0289, +0.6834]")
print(f"Delta lo: {ci.lo - (-0.0289):+.4f}")

# Full-sample Sharpes
v2_sr = sharpe_ratio(v2_ret.values)
spy_sr = sharpe_ratio(spy_ret.values)
print(f"\nv2 annualised Sharpe: {v2_sr:.3f}")
print(f"SPY annualised Sharpe: {spy_sr:.3f}")
print(f"Diff: {v2_sr - spy_sr:+.3f}")

# ── 2. Live-track July checkpoint ─────────────────────────────────────────
print("\n" + "=" * 60)
print("CHECK #2: Live-Track July Checkpoint")
print("=" * 60)

portfolio_path = Path(__file__).resolve().parent.parent / "portfolio.json"
portfolio = json.loads(portfolio_path.read_text())

# Build SPY close dict from the OHLCV cache for live-track use
spy_series = load_ohlcv("SPY", "2026-01-01")["Close"]
spy_closes = {str(d.date()): float(v) for d, v in spy_series.items()
              if not pd.isna(v)}

lt = lt_summary(portfolio, spy_closes, baseline_date="2026-07-13")

print(f"Completed months: {lt['completed_months']}")
print(f"Consecutive beats: {lt['consecutive_beat_months']} / 3 required")
print(f"Criterion 2 (3 months beat): {'PASS' if lt['criterion2_pass'] else 'FAIL'}")
print(f"Worst live drawdown: {lt['worst_live_drawdown']*100:.2f}%")
print(f"Criterion 3 (DD<20%): {'PASS' if lt['criterion3_pass'] else 'FAIL'}")
print(f"Live observations: {lt['live_obs']}")
print(f"MinTRL remaining (days vs SPY): {lt['min_trl_days_vs_spy']:.0f}")

if lt["checkpoints"]:
    print("\nMonthly checkpoints:")
    for cp in lt["checkpoints"]:
        beat = "✓ BEAT" if cp["beat"] else "✗ MISS"
        p = f"{cp['port_ret']*100:+.2f}%"
        s = f"{cp['spy_ret']*100:+.2f}%" if cp["spy_ret"] is not None else "n/a"
        print(f"  {cp['month']}  Port: {p}  SPY: {s}  {beat}")
else:
    print("No completed monthly checkpoints yet (< 1 full month since baseline).")

# ── 3. Portfolio mark (current) ────────────────────────────────────────────
print("\n" + "=" * 60)
print("CHECK #3: Portfolio Mark")
print("=" * 60)

last = portfolio["last_mark"]
positions = portfolio["positions"]
spy_latest = spy.iloc[-1]
port_value = positions["SPY"]["units"] * spy_latest

print(f"Latest SPY close: ${spy_latest:.4f} ({spy.index[-1].date()})")
print(f"SPY units held: {positions['SPY']['units']:.6f}")
print(f"Portfolio value: ${port_value:.2f}")
print(f"All-time P&L: ${port_value - 1000:.2f} ({(port_value/1000 - 1)*100:.3f}%)")

# SPY benchmark return since inception (2026-07-13 @ 749.17)
spy_baseline = 749.17
spy_since_live = spy_latest / spy_baseline - 1
port_since_live = port_value / 999.0 - 1  # inception at $999
print(f"\nSince live baseline (2026-07-13):")
print(f"  Portfolio: {port_since_live*100:+.3f}%")
print(f"  SPY:       {spy_since_live*100:+.3f}%")
print(f"  Alpha:     {(port_since_live - spy_since_live)*100:+.3f}%")

# ── 4. Guardrails check ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("CHECK #4: Operational Guardrails")
print("=" * 60)

vix_series = None
try:
    vix_data = load_ohlcv("^VIX", "2026-01-01")
    vix_series = vix_data["Close"]
except Exception:
    pass

spy_returns_recent = spy.pct_change().dropna()
guardrail_result = guardrails_run_all(
    portfolio=portfolio,
    spy_returns=spy_returns_recent,
    stale_days=0,
)
all_ok = guardrail_result["all_ok"]
print(f"All guardrails OK: {all_ok}")
for chk in guardrail_result["checks"]:
    status = "GREEN" if chk["ok"] else "AMBER/RED"
    print(f"  {chk['guardrail']:<22} {status}  {chk.get('detail', chk.get('level', ''))}")

# ── 5. Kelly analysis of v2 ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("CHECK #5: Kelly Analysis of v2 Champion")
print("=" * 60)

v2_sr_ann = float(sharpe_ratio(v2_ret.values))
v2_vol_ann = float(v2_ret.std() * np.sqrt(252))
k = kelly_summary(v2_sr_ann, v2_vol_ann, leverage_cap=1.0)

print(f"v2 Sharpe: {k['sharpe']:.3f}  Vol: {k['sigma_ann']:.3f}")
print(f"Full Kelly: {k['full_kelly']:.3f}x  (capped to {k['full_kelly_capped']:.3f})")
print("Fraction analysis:")
for name, f in k["fractions"].items():
    print(f"  {name:<8} position={f['position']:.3f}  "
          f"growth_rate={f['growth_rate_ann']:.3f}%/yr")

# v2 vol-target as Kelly equivalent
vol_target = 0.18
implied_frac = vol_target_to_kelly_equiv(vol_target, v2_sr_ann)
print(f"\nv2 vol-target={vol_target} implies Kelly fraction ≈ {implied_frac:.3f} "
      f"when σ = {vol_target}")
print("(At lower-vol periods, the cap binds at 1.0; the effective fraction is lower.)")

print("\nMonthly checks complete.")
