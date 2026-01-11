"""Performance metrics for backtesting."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics for a strategy."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # in months
    win_rate: float  # percentage of positive months
    best_month: float
    worst_month: float
    avg_monthly_return: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "win_rate": self.win_rate,
            "best_month": self.best_month,
            "worst_month": self.worst_month,
            "avg_monthly_return": self.avg_monthly_return,
        }


def calculate_metrics(
    portfolio_values: pd.DataFrame,
    risk_free_rate: float = 0.0
) -> PerformanceMetrics:
    """
    Calculate performance metrics from portfolio values.

    Args:
        portfolio_values: DataFrame with columns: date, portfolio_value
        risk_free_rate: Annual risk-free rate for Sharpe ratio calculation

    Returns:
        PerformanceMetrics object
    """
    values = portfolio_values["portfolio_value"].values

    # Calculate returns
    returns = np.diff(values) / values[:-1]

    # Total return
    total_return = (values[-1] / values[0]) - 1

    # Annualized return (assuming monthly data)
    n_months = len(values) - 1
    n_years = n_months / 12
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0

    # Volatility (annualized from monthly)
    monthly_vol = np.std(returns)
    volatility = monthly_vol * np.sqrt(12)

    # Sharpe ratio
    monthly_rf = risk_free_rate / 12
    excess_returns = returns - monthly_rf
    sharpe_ratio = (np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(12)
                    if np.std(excess_returns) > 0 else 0)

    # Maximum drawdown
    peak = np.maximum.accumulate(values)
    drawdown = (values - peak) / peak
    max_drawdown = np.min(drawdown)

    # Maximum drawdown duration
    drawdown_duration = 0
    current_duration = 0
    for dd in drawdown:
        if dd < 0:
            current_duration += 1
            drawdown_duration = max(drawdown_duration, current_duration)
        else:
            current_duration = 0

    # Win rate
    win_rate = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0

    # Best/worst months
    best_month = np.max(returns) if len(returns) > 0 else 0
    worst_month = np.min(returns) if len(returns) > 0 else 0

    # Average monthly return
    avg_monthly_return = np.mean(returns) if len(returns) > 0 else 0

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_duration=drawdown_duration,
        win_rate=win_rate,
        best_month=best_month,
        worst_month=worst_month,
        avg_monthly_return=avg_monthly_return,
    )


def calculate_drawdown_series(portfolio_values: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate drawdown series from portfolio values.

    Args:
        portfolio_values: DataFrame with columns: date, portfolio_value

    Returns:
        DataFrame with columns: date, drawdown, peak
    """
    df = portfolio_values.copy()
    df["peak"] = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"]
    return df[["date", "drawdown", "peak"]]


def calculate_rolling_returns(
    portfolio_values: pd.DataFrame,
    window_months: int = 12
) -> pd.DataFrame:
    """
    Calculate rolling returns.

    Args:
        portfolio_values: DataFrame with columns: date, portfolio_value
        window_months: Rolling window size in months

    Returns:
        DataFrame with columns: date, rolling_return
    """
    df = portfolio_values.copy()
    values = df["portfolio_value"]

    # Calculate rolling return
    df["rolling_return"] = values / values.shift(window_months) - 1

    return df[["date", "rolling_return"]].dropna()


def compare_strategies(
    strategy_values: pd.DataFrame,
    benchmark_values: pd.DataFrame,
    strategy_name: str = "Momentum",
    benchmark_name: str = "Buy & Hold"
) -> pd.DataFrame:
    """
    Compare two strategies side by side.

    Args:
        strategy_values: DataFrame with columns: date, portfolio_value
        benchmark_values: DataFrame with columns: date, portfolio_value
        strategy_name: Name of the strategy
        benchmark_name: Name of the benchmark

    Returns:
        DataFrame with comparison metrics
    """
    strategy_metrics = calculate_metrics(strategy_values)
    benchmark_metrics = calculate_metrics(benchmark_values)

    comparison = pd.DataFrame([
        {
            "metric": "Total Return",
            strategy_name: f"{strategy_metrics.total_return:.1%}",
            benchmark_name: f"{benchmark_metrics.total_return:.1%}",
        },
        {
            "metric": "Annualized Return",
            strategy_name: f"{strategy_metrics.annualized_return:.1%}",
            benchmark_name: f"{benchmark_metrics.annualized_return:.1%}",
        },
        {
            "metric": "Volatility",
            strategy_name: f"{strategy_metrics.volatility:.1%}",
            benchmark_name: f"{benchmark_metrics.volatility:.1%}",
        },
        {
            "metric": "Sharpe Ratio",
            strategy_name: f"{strategy_metrics.sharpe_ratio:.2f}",
            benchmark_name: f"{benchmark_metrics.sharpe_ratio:.2f}",
        },
        {
            "metric": "Max Drawdown",
            strategy_name: f"{strategy_metrics.max_drawdown:.1%}",
            benchmark_name: f"{benchmark_metrics.max_drawdown:.1%}",
        },
        {
            "metric": "Win Rate",
            strategy_name: f"{strategy_metrics.win_rate:.1%}",
            benchmark_name: f"{benchmark_metrics.win_rate:.1%}",
        },
    ])

    return comparison
