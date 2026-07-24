#!/usr/bin/env python3
"""Daily EOD market-data fetcher for Menéndez Capital (CashMoney).

WHY THIS EXISTS
---------------
The research bot runs in a sandbox whose network proxy allows *only*
github.com. Market-data APIs (Yahoo, Stooq, FRED) are unreachable from there.
This script is therefore NOT run by the bot -- it runs on GitHub Actions,
whose runners have full internet, and commits the fetched CSVs back into the
repo. The bot then `git pull`s fresh data through the one channel it can reach.

WHAT IT DOES
------------
Pulls daily OHLCV from 2000-01-01 to present for the tradable universe and
writes:
  data/cache/ohlcv/<TICKER>.csv   one file per instrument (Date,Open,High,Low,Close,Volume)
  data/cache/ohlcv_panel.csv      long-format panel of all instruments
  data/cache/last_updated.json    manifest: when, coverage, per-ticker last date

Sources, in order of preference per ticker: yfinance (Yahoo) -> Stooq.
No API keys required.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd

START = "2000-01-01"
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
OHLCV = CACHE / "ohlcv"

# Tradable universe (matches STATE.md / SKILL.md). Newer ETFs (XLRE 2015,
# XLC 2018) simply carry shorter histories -- that's fine.
UNIVERSE = {
    "broad":     ["SPY", "DIA", "QQQ", "IWM"],
    "sector":    ["XLK", "XLF", "XLE", "XLV", "XLY",
                  "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC"],
    "defensive": ["TLT", "IEF", "SHY", "GLD", "AGG"],
    "global":    ["EFA", "EEM", "ACWI"],  # developed intl, emerging, all-world (unblocks true GEM/GTAA)
    "country":   ["EWC", "EWJ", "EWU", "EWG"],  # Canada, Japan, UK, Germany (tradable, dividends included)
    "intl_idx":  ["^GSPTSE", "^FTSE", "^N225", "^GDAXI", "^HSI"],  # TSX, FTSE 100, Nikkei, DAX, Hang Seng (benchmark-only, price indexes)
    "real":      ["DBC", "VNQ"],          # commodities, US real estate (full Faber 5)
    "mega":      ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
    "vol":       ["^VIX"],
    "rates":     ["^IRX"],   # 13-week T-bill discount rate -> cash-sleeve yield
}
ALL = [t for group in UNIVERSE.values() for t in group]

COLS = ["Open", "High", "Low", "Close", "Volume"]


def _safe(ticker: str) -> str:
    return ticker.replace("^", "_")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not len(df):
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    keep = [c for c in COLS if c in df.columns]
    df = df[keep].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[df.index >= pd.Timestamp(START)]
    return df.dropna(how="all")


def fetch_yf(ticker: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, start=START, auto_adjust=True,
                     progress=False, threads=False)
    return _normalize(df)


def fetch_stooq(ticker: str) -> pd.DataFrame:
    import urllib.request
    sym = ticker.lower()
    sym = sym if sym.startswith("^") else f"{sym}.us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode("utf-8", "replace")
    if "Date" not in text:
        return pd.DataFrame()
    df = pd.read_csv(StringIO(text), parse_dates=["Date"], index_col="Date")
    return _normalize(df)


def fetch(ticker: str):
    for fn in (fetch_yf, fetch_stooq):
        try:
            df = fn(ticker)
            if len(df):
                return df, fn.__name__.replace("fetch_", "")
        except Exception as e:  # noqa: BLE001
            print(f"  {ticker}: {fn.__name__} failed: {e}")
    return pd.DataFrame(), None




# ---------------------------------------------------------------------------
# Fundamentals: Shiller monthly S&P dataset (price, D, E, CPI, CAPE, 1871->)
# Unblocks ROADMAP #6 (value tilt). Sources: canonical ie_data.xls at Yale,
# datahub.io parsed CSV as fallback. Written as a tidy monthly CSV so the
# sandbox never needs xls parsing.
# ---------------------------------------------------------------------------
FUND = CACHE / "fundamentals"
SHILLER_XLS_URLS = [
    "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
    "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/ie_data.xls",  # shillerdata.com mirror (path may rotate)
]
DATAHUB_CSV = "https://datahub.io/core/s-and-p-500/r/data.csv"


def _normalize_shiller(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy a raw Shiller frame -> monthly CSV with stable columns.

    Expects columns (any case): Date (fractional year like 1871.01), P, D, E,
    CPI, CAPE. Returns Date-indexed monthly rows, numeric, CAPE may be NaN for
    the first 10 years. No forward-fill (no lookahead): each row is as-published.
    """
    df = df.rename(columns={c: str(c).strip().title() for c in df.columns})
    ren = {"P": "Price", "D": "Dividend", "E": "Earnings",
           "Cape": "CAPE", "Sp500": "Price", "Real Price": "RealPrice"}
    df = df.rename(columns=ren)
    if "Date" not in df.columns:
        raise ValueError("Shiller frame lacks Date column")
    # Shiller dates are fractional years: 1871.01 .. 1871.1 means Jan..Oct.
    def _to_ts(x):
        try:
            y = int(float(x))
            frac = round((float(x) - y) * 100)
            m = 10 if frac == 1 and f"{x}".endswith(".1") else max(1, min(12, frac))
            return pd.Timestamp(year=y, month=m, day=1)
        except (TypeError, ValueError):
            return pd.NaT
    idx = df["Date"].map(_to_ts)
    keep = [c for c in ["Price", "Dividend", "Earnings", "Cpi", "CAPE"] if c in df.columns]
    out = df[keep].apply(pd.to_numeric, errors="coerce")
    out.index = idx
    out.index.name = "Date"
    out = out[out.index.notna()].sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out.dropna(subset=["Price"])


def fetch_shiller() -> pd.DataFrame:
    """Try Yale xls, then datahub CSV. Returns tidy monthly frame or empty."""
    for url in SHILLER_XLS_URLS:
        try:
            raw = pd.read_excel(url, sheet_name="Data", skiprows=7)
            raw = raw.rename(columns={raw.columns[0]: "Date"})
            cols = {raw.columns[i]: n for i, n in
                    zip(range(1, 5), ["P", "D", "E", "CPI"])}
            raw = raw.rename(columns=cols)
            if "CAPE" not in raw.columns:
                for c in raw.columns:
                    if str(c).upper().startswith("CAPE"):
                        raw = raw.rename(columns={c: "CAPE"})
                        break
            df = _normalize_shiller(raw)
            if len(df) > 1000:
                return df
        except Exception as e:  # noqa: BLE001
            print(f"  shiller: {url} failed: {e}")
    try:
        raw = pd.read_csv(DATAHUB_CSV)
        raw = raw.rename(columns={"SP500": "P", "Consumer Price Index": "CPI"})
        raw["Date"] = pd.to_datetime(raw["Date"])
        raw = raw.set_index("Date")
        ren = {"Dividend": "Dividend", "Earnings": "Earnings",
               "P": "Price", "CPI": "Cpi", "PE10": "CAPE"}
        raw = raw.rename(columns=ren)
        keep = [c for c in ["Price", "Dividend", "Earnings", "Cpi", "CAPE"]
                if c in raw.columns]
        df = raw[keep].apply(pd.to_numeric, errors="coerce").sort_index()
        if len(df) > 1000:
            return df.dropna(subset=["Price"])
    except Exception as e:  # noqa: BLE001
        print(f"  shiller: datahub fallback failed: {e}")
    return pd.DataFrame()


def refresh_fundamentals() -> bool:
    FUND.mkdir(parents=True, exist_ok=True)
    df = fetch_shiller()
    if not len(df):
        print("!! shiller: NO DATA (kept previous file if any)")
        return False
    df.to_csv(FUND / "shiller_monthly.csv")
    print(f"   shiller: {len(df)} monthly rows "
          f"{df.index[0].date()}..{df.index[-1].date()}")
    return True


def main() -> int:
    OHLCV.mkdir(parents=True, exist_ok=True)
    manifest, frames, ok = {}, [], 0
    for t in ALL:
        df, src = fetch(t)
        if not len(df):
            print(f"!! {t}: NO DATA")
            manifest[t] = {"rows": 0, "first": None, "last": None, "source": None}
            continue
        df.to_csv(OHLCV / f"{_safe(t)}.csv")
        manifest[t] = {"rows": int(len(df)), "first": str(df.index[0].date()),
                       "last": str(df.index[-1].date()), "source": src}
        w = df.reset_index()[["Date", "Close"]].copy()
        w["Ticker"] = t
        frames.append(w)
        ok += 1
        print(f"   {t}: {len(df)} rows {df.index[0].date()}..{df.index[-1].date()} ({src})")
        time.sleep(0.4)

    if frames:
        pd.concat(frames, ignore_index=True).to_csv(
            CACHE / "ohlcv_panel.csv", index=False)

    meta = {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start": START,
        "tickers_ok": ok,
        "tickers_total": len(ALL),
        "tickers": manifest,
    }
    (CACHE / "last_updated.json").write_text(json.dumps(meta, indent=2))
    fund_ok = refresh_fundamentals()
    meta["fundamentals_ok"] = bool(fund_ok)
    (CACHE / "last_updated.json").write_text(json.dumps(meta, indent=2))
    print(f"\nDone: {ok}/{len(ALL)} tickers refreshed; fundamentals={'ok' if fund_ok else 'FAILED'}.")
    return 0 if ok >= len(ALL) // 2 else 1


if __name__ == "__main__":
    sys.exit(main())
