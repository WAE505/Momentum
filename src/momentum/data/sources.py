"""Data fetching from Yahoo Finance and FRED."""

import pandas as pd
import numpy as np
import yfinance as yf
from pandas_datareader import data as pdr
from datetime import datetime, timedelta


def fetch_sp500(start_date: str = "1988-01-01", end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch S&P 500 Total Return Index from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        DataFrame with columns: date, price (total return index)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Try to get S&P 500 Total Return Index first
    ticker = yf.Ticker("^SP500TR")
    df = ticker.history(start=start_date, end=end_date, interval="1mo")

    if df.empty:
        # Fallback to regular S&P 500 (without dividends)
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(start=start_date, end=end_date, interval="1mo")

    if df.empty:
        raise ValueError("Could not fetch S&P 500 data")

    # Reset index to get date as column
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Close": "price"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[["date", "price"]].copy()
    df["asset"] = "equity"

    return df


def fetch_gold(start_date: str = "1979-01-01", end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch Gold prices from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        DataFrame with columns: date, price
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Gold futures
    ticker = yf.Ticker("GC=F")
    df = ticker.history(start=start_date, end=end_date, interval="1mo")

    if df.empty:
        # Try GLD ETF as fallback (starts 2004)
        ticker = yf.Ticker("GLD")
        df = ticker.history(start=start_date, end=end_date, interval="1mo")

    if df.empty:
        raise ValueError("Could not fetch Gold data")

    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Close": "price"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[["date", "price"]].copy()
    df["asset"] = "gold"

    return df


def fetch_treasury(start_date: str = "1962-01-01", end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch 10-Year Treasury data from FRED and convert yields to a total return index.

    The 10-year Treasury yield is converted to a total return index using
    the approximate formula for bond returns.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        DataFrame with columns: date, price (total return index)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch 10-year Treasury yield from FRED
    df = pdr.DataReader("DGS10", "fred", start_date, end_date)
    df = df.reset_index()
    df = df.rename(columns={"DATE": "date", "DGS10": "yield"})

    # Resample to monthly (end of month)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df.resample("ME").last()
    df = df.reset_index()

    # Drop any NaN values
    df = df.dropna()

    # Convert yields to total return index
    # Approximate monthly return = (yield/12) - duration * delta_yield
    # Duration for 10-year bond is approximately 8 years
    duration = 8.0
    df["yield_decimal"] = df["yield"] / 100
    df["yield_change"] = df["yield_decimal"].diff()

    # Monthly return = coupon income - price change from yield movement
    df["monthly_return"] = df["yield_decimal"] / 12 - duration * df["yield_change"]
    df.loc[df.index[0], "monthly_return"] = 0  # First month has no return

    # Calculate cumulative total return index (starting at 100)
    df["price"] = 100 * (1 + df["monthly_return"]).cumprod()

    df = df[["date", "price"]].copy()
    df["asset"] = "bond"

    return df


def fetch_tbill(start_date: str = "1954-01-01", end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch 3-Month T-Bill rate from FRED and convert to a total return index.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        DataFrame with columns: date, price (total return index), rate
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch 3-month T-bill rate from FRED
    df = pdr.DataReader("DTB3", "fred", start_date, end_date)
    df = df.reset_index()
    df = df.rename(columns={"DATE": "date", "DTB3": "rate"})

    # Resample to monthly (end of month)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df.resample("ME").last()
    df = df.reset_index()

    # Drop any NaN values
    df = df.dropna()

    # Convert annual rate to monthly return
    df["rate_decimal"] = df["rate"] / 100
    df["monthly_return"] = df["rate_decimal"] / 12

    # Calculate cumulative total return index (starting at 100)
    df["price"] = 100 * (1 + df["monthly_return"]).cumprod()

    df = df[["date", "price", "rate"]].copy()
    df["asset"] = "cash"

    return df


def fetch_all_data(start_date: str = "1988-01-01", end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch all asset data and combine into a single DataFrame.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        DataFrame with columns: date, equity, bond, gold, cash, cash_rate
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch all data
    sp500 = fetch_sp500(start_date, end_date)
    treasury = fetch_treasury(start_date, end_date)
    gold = fetch_gold(start_date, end_date)
    tbill = fetch_tbill(start_date, end_date)

    # Pivot each to have date as index
    sp500 = sp500.set_index("date")[["price"]].rename(columns={"price": "equity"})
    treasury = treasury.set_index("date")[["price"]].rename(columns={"price": "bond"})
    gold = gold.set_index("date")[["price"]].rename(columns={"price": "gold"})
    tbill_prices = tbill.set_index("date")[["price", "rate"]].rename(
        columns={"price": "cash", "rate": "cash_rate"}
    )

    # Combine all data
    combined = sp500.join(treasury, how="outer")
    combined = combined.join(gold, how="outer")
    combined = combined.join(tbill_prices, how="outer")

    # Forward fill missing values (for alignment)
    combined = combined.ffill()

    # Drop rows where any core asset is missing
    combined = combined.dropna(subset=["equity", "bond", "gold", "cash"])

    combined = combined.reset_index()

    return combined
