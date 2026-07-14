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
    """
    df = pd.read_csv(US_MARKET_CSV, parse_dates=["Date"], index_col="Date")
    out = pd.DataFrame(
        {
            "Close": df["Adjusted Close"],
            "PriceClose": df["Close"],
            "RiskFreeRate": df["Risk Free Rate"],
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
