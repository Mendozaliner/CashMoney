"""Operational risk guardrails for the Menendez Capital paper desk.

Codified from the s10 famous-failures research pass (see
research/2026-07-16-s10-famous-failures-guardrails.md):
LTCM 1998 (leverage/liquidity), Niederhoffer 1997 (negative convexity,
revenge sizing), Quant Quake Aug-2007 (crowding/correlation spikes,
Khandani & Lo NBER WP 14465), Amaranth 2006 (concentration, Chincarini
SSRN 1633589), and the PWG/CFTC hedge-fund best-practices framework.

These are MONITORS and HARD OPERATIONAL CONSTRAINTS. None of them alters
the frozen champion's signal (Phase 2). Escalation is by REPORTING, not
auto-liquidation: E4/E8 showed reactive kill-switches cost Sharpe without
improving drawdown.
"""

from __future__ import annotations

# --- Hard limits (G1-G7) ---
MAX_GROSS_EXPOSURE = 1.0          # G1: no leverage, ever (LTCM)
ALLOW_SHORTS = False              # G1
ALLOW_DERIVATIVES = False         # G2: no unbounded-loss instruments (Niederhoffer)
MAX_SINGLE_STOCK_PCT = 0.20       # G4 (Amaranth)
MAX_SINGLE_SECTOR_ETF_PCT = 0.30  # G4
VOL_SPIKE_MULT = 2.0              # G5: 20d vol vs 1y median (Quant Quake)
DAILY_MOVE_SIGMA = 4.0            # G5
DD_AMBER, DD_RED, DD_BREACH = -0.10, -0.15, -0.20  # G6 ladder
MAX_STALE_DAYS = 4                # G7

BROAD_INDEX_ETFS = {"SPY", "DIA", "QQQ", "IWM", "ACWI", "EFA", "EEM", "EWC",
                    "EWJ", "EWU", "EWG", "AGG", "TLT", "IEF", "SHY", "GLD",
                    "DBC", "VNQ"}
SECTOR_ETFS = {"XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU",
               "XLB", "XLRE", "XLC"}
SINGLE_STOCKS = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"}
WHITELIST = BROAD_INDEX_ETFS | SECTOR_ETFS | SINGLE_STOCKS


def check_exposure(gross_exposure: float) -> dict:
    """G1: gross exposure must be within [0, 1.0]."""
    ok = 0.0 <= gross_exposure <= MAX_GROSS_EXPOSURE + 1e-9
    return {"guardrail": "G1_leverage", "ok": ok,
            "detail": f"gross={gross_exposure:.4f} cap={MAX_GROSS_EXPOSURE}"}


def check_instruments(tickers) -> dict:
    """G2: whitelist only; no derivatives/short-vol possible by construction."""
    bad = sorted(set(tickers) - WHITELIST)
    return {"guardrail": "G2_instruments", "ok": not bad,
            "detail": f"non-whitelisted={bad}" if bad else "all whitelisted"}


def check_concentration(weights: dict) -> dict:
    """G4: single stock <= 20% NAV, single sector ETF <= 30%; broad index exempt."""
    viol = []
    for t, w in weights.items():
        if t in SINGLE_STOCKS and w > MAX_SINGLE_STOCK_PCT + 1e-9:
            viol.append(f"{t}={w:.2%}>{MAX_SINGLE_STOCK_PCT:.0%}")
        elif t in SECTOR_ETFS and w > MAX_SINGLE_SECTOR_ETF_PCT + 1e-9:
            viol.append(f"{t}={w:.2%}>{MAX_SINGLE_SECTOR_ETF_PCT:.0%}")
        elif w < -1e-9:
            viol.append(f"{t} short position")
    return {"guardrail": "G4_concentration", "ok": not viol,
            "detail": "; ".join(viol) or "within caps"}


def vol_spike_flag(ret_series) -> dict:
    """G5: AMBER if 20d realized vol > 2x its trailing-1y median, or |last move| > 4 sigma.

    ret_series: pandas Series of daily returns (most recent last).
    Monitor only -- never a trading signal.
    """
    import numpy as np
    r = ret_series.dropna()
    if len(r) < 272:
        return {"guardrail": "G5_vol_spike", "ok": True, "detail": "insufficient history"}
    vol20 = r.rolling(20).std() * np.sqrt(252)
    cur, med = float(vol20.iloc[-1]), float(vol20.iloc[-252:].median())
    sigma = float(r.iloc[-252:].std())
    big_move = abs(float(r.iloc[-1])) > DAILY_MOVE_SIGMA * sigma if sigma > 0 else False
    spike = cur > VOL_SPIKE_MULT * med
    return {"guardrail": "G5_vol_spike", "ok": not (spike or big_move),
            "detail": f"vol20={cur:.3f} med1y={med:.3f} last_move_4sig={big_move}"}


def drawdown_level(current_value: float, peak_value: float) -> dict:
    """G6: reporting escalation ladder. Never auto-liquidates."""
    dd = current_value / peak_value - 1.0
    if dd <= DD_BREACH:
        lvl = "BREACH: Phase criterion 3 broken - immediate report to Mr. Menendez"
    elif dd <= DD_RED:
        lvl = "RED: dedicated review session required"
    elif dd <= DD_AMBER:
        lvl = "AMBER: flag in next briefing"
    else:
        lvl = "GREEN"
    return {"guardrail": "G6_drawdown", "ok": dd > DD_AMBER,
            "level": lvl, "drawdown": round(dd, 4)}


def staleness_guard(stale_days: int) -> dict:
    """G7: stale data -> no live marks, no rebalancing on stale signals."""
    ok = stale_days <= MAX_STALE_DAYS
    return {"guardrail": "G7_staleness", "ok": ok,
            "detail": f"stale_days={stale_days} max={MAX_STALE_DAYS}"}


def run_all(portfolio: dict, spy_returns=None, stale_days: int = 0,
            peak_value: float | None = None) -> dict:
    """Run every guardrail against a portfolio.json-shaped dict. Returns report."""
    val = portfolio["last_mark"]["value"]
    pos_val = {t: p["units"] * p["last_px"] for t, p in portfolio["positions"].items()}
    nav = sum(pos_val.values()) + portfolio.get("cash", 0.0)
    weights = {t: v / nav for t, v in pos_val.items()}
    gross = sum(abs(w) for w in weights.values())
    peak = peak_value if peak_value is not None else max(
        [h["value"] for h in portfolio.get("history", [])] + [val])
    checks = [
        check_exposure(gross),
        check_instruments(weights.keys()),
        check_concentration(weights),
        drawdown_level(val, peak),
        staleness_guard(stale_days),
    ]
    if spy_returns is not None:
        checks.append(vol_spike_flag(spy_returns))
    return {"nav": round(nav, 2), "all_ok": all(c["ok"] for c in checks),
            "checks": checks}
