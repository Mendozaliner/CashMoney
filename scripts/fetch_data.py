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
    "defensive": ["TLT", "IEF", "SHY", "GLD"],
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
    print(f"\nDone: {ok}/{len(ALL)} tickers refreshed.")
    return 0 if ok >= len(ALL) // 2 else 1


if __name__ == "__main__":
    sys.exit(main())
