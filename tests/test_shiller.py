"""Offline tests for the Shiller fundamentals parser + loader (no network)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pandas as pd
import pytest

from scripts.fetch_data import _normalize_shiller


def _raw():
    # Fractional-year dates: .1 == October, .01 == January, .12 == December
    return pd.DataFrame({
        "Date": [1990.01, 1990.02, "1990.1", 1990.11, 1990.12, 1991.01, "junk"],
        "P": [330.2, 331.9, 304.0, 315.3, 328.8, 325.5, None],
        "D": [11.1, 11.2, 11.7, 11.8, 11.9, 12.0, None],
        "E": [22.5, 22.4, 21.3, 21.1, 21.0, 20.9, None],
        "CPI": [127.4, 128.0, 133.5, 133.8, 133.8, 134.6, None],
        "CAPE": [17.0, 16.9, 14.8, 15.2, 15.9, 15.6, None],
    })


def test_normalize_shape_and_columns():
    df = _normalize_shiller(_raw())
    assert list(df.columns) == ["Price", "Dividend", "Earnings", "Cpi", "CAPE"]
    assert len(df) == 6  # junk row dropped
    assert df.index.is_monotonic_increasing


def test_fractional_year_october_disambiguation():
    df = _normalize_shiller(_raw())
    months = [ts.month for ts in df.index]
    assert months == [1, 2, 10, 11, 12, 1]
    assert df.index[2] == pd.Timestamp("1990-10-01")


def test_numeric_coercion_and_no_ffill():
    df = _normalize_shiller(_raw())
    assert df["CAPE"].iloc[0] == pytest.approx(17.0)
    # no forward-fill is applied by the parser (as-published values only)
    raw = _raw()
    raw.loc[3, "CAPE"] = None
    df2 = _normalize_shiller(raw)
    assert pd.isna(df2["CAPE"].iloc[3])


def test_loader_roundtrip(tmp_path, monkeypatch):
    import data.loader as dl
    df = _normalize_shiller(_raw())
    fund = tmp_path / "fundamentals"
    fund.mkdir()
    df.to_csv(fund / "shiller_monthly.csv")
    monkeypatch.setattr(dl, "FUND_DIR", fund)
    out = dl.load_shiller()
    assert len(out) == 6 and "CAPE" in out.columns


def test_loader_missing_raises(tmp_path, monkeypatch):
    import data.loader as dl
    monkeypatch.setattr(dl, "FUND_DIR", tmp_path / "nope")
    with pytest.raises(FileNotFoundError):
        dl.load_shiller()
