"""Data loading utilities for the CashMoney research repo.

Environment note (2026-07-13): the research sandbox's network proxy blocks
all market-data APIs (Yahoo/yfinance, Stooq, Alpha Vantage, FRED). The only
working network route is git access to github.com. The primary dataset is
therefore a committed snapshot of SteelCerberus/us-market-data: a daily
S&P 500 total-return series (constructed to approximate SPY, incl. dividends
and a 0.0945% expense ratio), 1885-03-20 to present. See that repo's README
for caveats (early data is a Dow composite; CPI interpolation; etc.).

`load_yfinance` is provided for environments where yfinance works; it caches
to data/cache/<ticker>.csv and will transparently use the cache offline.
"""
from pathlib import Path
import subprocess
import tempfile

import pandas as pd

CACHE = Path(__file__).resolve().parent / "cache"
US_MARKET_CSV = CACHE / "us_market_data.csv"
US_MARKET_REPO = "https://github.com/SteelCerberus/us-market-data"


def load_spy_proxy(start=None, end=None) -> pd.DataFrame:
    """Daily SPY-proxy total-return series.

    Returns a DataFrame indexed by date with:
      Close   -- total-return adjusted close (dividends reinvested)
      PriceClose -- price-only close
      RiskFreeRate -- annualized risk-free rate, percent
      RiskFreeIndex -- cumulative T-bill total-return index (daily ratio
                       = daily risk-free return; used for cash-sleeve yield)
    """
    df = pd.read_csv(US_MARKET_CSV, parse_dates=["Date"], index_col="Date")
    out = pd.DataFrame(
        {
            "Close": df["Adjusted Close"],
            "PriceClose": df["Close"],
            "RiskFreeRate": df["Risk Free Rate"],
            "RiskFreeIndex": df["Risk Free Return"],
        }
    )
    return out.loc[start:end]


def refresh_spy_proxy_cache() -> None:
    """Re-clone the upstream repo and refresh the committed snapshot."""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["git", "clone", "--depth", "1", US_MARKET_REPO, td],
            check=True, capture_output=True,
        )
        src = Path(td) / "data" / "us_market_data.csv"
        US_MARKET_CSV.write_bytes(src.read_bytes())


def load_yfinance(ticker: str, start="2000-01-01", end=None) -> pd.DataFrame:
    """OHLCV via yfinance with local CSV caching. Blocked by the sandbox
    proxy as of 2026-07-13; kept for portability."""
    cache_file = CACHE / f"{ticker}.csv"
    try:
        import yfinance as yf

        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
        if len(df):
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.to_csv(cache_file)
            return df
    except Exception:
        pass
    if cache_file.exists():
        df = pd.read_csv(cache_file, parse_dates=[0], index_col=0)
        return df.loc[start:end]
    raise RuntimeError(
        f"No network access to Yahoo and no cache for {ticker}."
    )


VIX_CSV = CACHE / "vix_daily.csv"


def load_vix(start=None, end=None) -> pd.DataFrame:
    """Daily VIX OHLC (CBOE via github.com/datasets/finance-vix snapshot,
    1990 -> present; refresh by re-cloning that repo). Added session 2."""
    df = pd.read_csv(VIX_CSV, parse_dates=["DATE"], index_col="DATE")
    df.index.name = "Date"
    return df.loc[start:end]


# ---------------------------------------------------------------------------
# Multi-asset daily OHLCV (added 2026-07-13) -- refreshed by GitHub Actions
# (scripts/fetch_data.py) and committed to data/cache/ohlcv/. The research
# sandbox reads these via `git pull`; it never fetches them directly.
# Scope: 2000-01-01 -> present. Post-decimalization era (chosen deliberately;
# see SKILL.md testing protocol).
# ---------------------------------------------------------------------------
import json as _json

OHLCV_DIR = CACHE / "ohlcv"
DATA_MANIFEST = CACHE / "last_updated.json"


def _ohlcv_path(ticker: str) -> Path:
    return OHLCV_DIR / f"{ticker.replace('^', '_')}.csv"


def load_ohlcv(ticker: str, start="2000-01-01", end=None) -> pd.DataFrame:
    """Daily OHLCV for one instrument from the committed cache.

    Columns: Open, High, Low, Close, Volume (adjusted close as Close).
    Raises FileNotFoundError with a helpful hint if the cache is missing.
    """
    p = _ohlcv_path(ticker)
    if not p.exists():
        raise FileNotFoundError(
            f"No cached OHLCV for {ticker!r} at {p}. The GitHub Action "
            "'Update market data' populates data/cache/ohlcv/ -- run it "
            "(Actions tab -> Run workflow) or `git pull` after it has run."
        )
    df = pd.read_csv(p, parse_dates=["Date"], index_col="Date")
    return df.loc[start:end]


def load_universe(tickers=None, field="Close", start="2000-01-01",
                  end=None) -> pd.DataFrame:
    """Wide DataFrame of one field (default Close) across many tickers,
    aligned on the trading calendar. Missing tickers are skipped with a note."""
    if tickers is None:
        tickers = [p.stem.replace("_", "^") if p.stem.startswith("_")
                   else p.stem for p in sorted(OHLCV_DIR.glob("*.csv"))]
    cols = {}
    for t in tickers:
        try:
            cols[t] = load_ohlcv(t, start, end)[field]
        except (FileNotFoundError, KeyError) as e:
            print(f"load_universe: skipping {t}: {e}")
    return pd.DataFrame(cols).sort_index()


def data_freshness() -> dict:
    """Return the data manifest (or an empty dict) plus a staleness flag.

    Use at session start: if `stale_days` is large the Action hasn't run, so
    marks/backtests are dated -- say so in the report rather than pretending."""
    if not DATA_MANIFEST.exists():
        return {"available": False, "stale_days": None,
                "note": "No data manifest; pipeline has not run yet."}
    meta = _json.loads(DATA_MANIFEST.read_text())
    last_dates = [v["last"] for v in meta.get("tickers", {}).values() if v.get("last")]
    newest = max(last_dates) if last_dates else None
    stale = None
    if newest:
        today_utc = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
        stale = (today_utc - pd.Timestamp(newest)).days
    return {"available": True, "newest_close": newest, "stale_days": stale,
            "tickers_ok": meta.get("tickers_ok"),
            "updated_utc": meta.get("updated_utc")}
