"""Momentum signal calculations."""

import pandas as pd
import numpy as np
from typing import Literal

AssetType = Literal["equity", "bond", "gold"]
LOOKBACK_PERIODS = [8, 9, 10]


def _sma_crossover_signal(prices: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate rolling average crossover signal.

    Signal = 1 if current price > SMA(lookback), else 0

    Args:
        prices: Price series
        lookback: Number of periods for SMA

    Returns:
        Series of signals (0 or 1)
    """
    sma = prices.rolling(window=lookback).mean()
    signal = (prices > sma).astype(int)
    return signal


def _point_in_time_signal(prices: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate point-in-time comparison signal.

    Signal = 1 if current price > price N months ago, else 0

    Args:
        prices: Price series
        lookback: Number of periods to look back

    Returns:
        Series of signals (0 or 1)
    """
    past_price = prices.shift(lookback)
    signal = (prices > past_price).astype(int)
    return signal


def _avg_two_months_vs_sma_signal(prices: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate signal using average of last 2 months vs SMA.

    This is specifically for equities as mentioned in the blog.
    Signal = 1 if avg(current, previous) > SMA(lookback), else 0

    Args:
        prices: Price series
        lookback: Number of periods for SMA

    Returns:
        Series of signals (0 or 1)
    """
    avg_two = (prices + prices.shift(1)) / 2
    sma = prices.rolling(window=lookback).mean()
    signal = (avg_two > sma).astype(int)
    return signal


def _calculate_excess_return_prices(
    prices: pd.Series,
    cash_prices: pd.Series
) -> pd.Series:
    """
    Calculate prices in excess of cash returns.

    Args:
        prices: Asset price series
        cash_prices: Cash total return index

    Returns:
        Series of excess return prices
    """
    # Calculate returns
    asset_returns = prices.pct_change()
    cash_returns = cash_prices.pct_change()

    # Excess return = asset return - cash return
    excess_returns = asset_returns - cash_returns
    excess_returns.iloc[0] = 0

    # Convert back to price index
    excess_prices = (1 + excess_returns).cumprod() * prices.iloc[0]

    return excess_prices


def calculate_momentum_signals(
    prices: pd.Series,
    cash_prices: pd.Series,
    asset_type: AssetType
) -> pd.DataFrame:
    """
    Calculate all 12 momentum signals for an asset.

    Signal types:
    1. SMA crossover (raw prices) - 3 lookbacks
    2. Point-in-time (raw prices) - 3 lookbacks
    3. SMA crossover (excess return prices) - 3 lookbacks
    4. Point-in-time (excess return prices) - 3 lookbacks

    For equities only, also includes:
    5. Avg 2 months vs SMA (raw prices) - 3 lookbacks

    Args:
        prices: Asset price series (index aligned with dates)
        cash_prices: Cash total return index
        asset_type: Type of asset ("equity", "bond", or "gold")

    Returns:
        DataFrame with individual signals as columns
    """
    signals = pd.DataFrame(index=prices.index)

    # Calculate excess return prices
    excess_prices = _calculate_excess_return_prices(prices, cash_prices)

    for lookback in LOOKBACK_PERIODS:
        # Raw price signals
        signals[f"sma_cross_{lookback}"] = _sma_crossover_signal(prices, lookback)
        signals[f"pit_{lookback}"] = _point_in_time_signal(prices, lookback)

        # Excess return signals
        signals[f"sma_cross_excess_{lookback}"] = _sma_crossover_signal(
            excess_prices, lookback
        )
        signals[f"pit_excess_{lookback}"] = _point_in_time_signal(
            excess_prices, lookback
        )

        # Equity-specific: average of 2 months vs SMA
        if asset_type == "equity":
            signals[f"avg2_sma_{lookback}"] = _avg_two_months_vs_sma_signal(
                prices, lookback
            )
            signals[f"avg2_sma_excess_{lookback}"] = _avg_two_months_vs_sma_signal(
                excess_prices, lookback
            )

    return signals


def calculate_combined_signal(signals: pd.DataFrame) -> pd.Series:
    """
    Calculate combined momentum signal (0.0 to 1.0).

    Args:
        signals: DataFrame of individual signals

    Returns:
        Series of combined signals (mean of all individual signals)
    """
    return signals.mean(axis=1)


def calculate_all_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate momentum signals for all assets in the dataset.

    Args:
        df: DataFrame with columns: date, equity, bond, gold, cash

    Returns:
        DataFrame with combined signals for each asset
    """
    df = df.copy()
    df = df.set_index("date")

    results = pd.DataFrame(index=df.index)

    # Calculate signals for each asset
    for asset, asset_type in [("equity", "equity"), ("bond", "bond"), ("gold", "gold")]:
        individual_signals = calculate_momentum_signals(
            df[asset],
            df["cash"],
            asset_type
        )
        results[f"{asset}_signal"] = calculate_combined_signal(individual_signals)

    # Also include individual signal details for equity (for debugging/display)
    equity_signals = calculate_momentum_signals(df["equity"], df["cash"], "equity")
    for col in equity_signals.columns:
        results[f"equity_{col}"] = equity_signals[col]

    return results.reset_index()
