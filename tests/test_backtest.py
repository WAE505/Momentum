"""Tests for backtesting engine."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from momentum.backtest.engine import run_backtest, run_buy_and_hold
from momentum.backtest.metrics import calculate_metrics, calculate_drawdown_series


def create_sample_data(n_months: int = 36) -> pd.DataFrame:
    """Create sample market data for testing."""
    dates = pd.date_range(start="2020-01-01", periods=n_months, freq="ME")

    # Create upward trending data with some volatility
    np.random.seed(42)

    equity = 100 * np.cumprod(1 + np.random.normal(0.01, 0.04, n_months))
    bond = 100 * np.cumprod(1 + np.random.normal(0.003, 0.02, n_months))
    gold = 100 * np.cumprod(1 + np.random.normal(0.005, 0.03, n_months))
    cash = 100 * np.cumprod(1 + np.full(n_months, 0.002))

    return pd.DataFrame({
        "date": dates,
        "equity": equity,
        "bond": bond,
        "gold": gold,
        "cash": cash,
    })


class TestBacktestEngine:
    """Tests for backtest engine."""

    def test_backtest_runs(self):
        """Backtest should run without errors."""
        data = create_sample_data()
        result = run_backtest(data)

        assert result.portfolio_values is not None
        assert len(result.portfolio_values) == len(data)

    def test_backtest_initial_value(self):
        """Backtest should start with correct initial value."""
        data = create_sample_data()
        result = run_backtest(data, initial_value=1000)

        assert result.portfolio_values.iloc[0]["portfolio_value"] == 1000

    def test_backtest_allocations_sum_to_one(self):
        """Allocations should sum to 1 at each point."""
        data = create_sample_data()
        result = run_backtest(data)

        for _, row in result.allocations.iterrows():
            total = (
                row["equity_weight"] +
                row["bond_weight"] +
                row["gold_weight"] +
                row["cash_weight"]
            )
            assert np.isclose(total, 1.0), f"Allocation sum is {total}"

    def test_backtest_with_costs(self):
        """Backtest with costs should have lower returns than without."""
        data = create_sample_data()

        result_with_costs = run_backtest(data, apply_costs=True)
        result_no_costs = run_backtest(data, apply_costs=False)

        final_with_costs = result_with_costs.portfolio_values.iloc[-1]["portfolio_value"]
        final_no_costs = result_no_costs.portfolio_values.iloc[-1]["portfolio_value"]

        assert final_with_costs <= final_no_costs


class TestBuyAndHold:
    """Tests for buy-and-hold strategy."""

    def test_buy_and_hold_runs(self):
        """Buy and hold should run without errors."""
        data = create_sample_data()
        result = run_buy_and_hold(data)

        assert len(result) == len(data)

    def test_buy_and_hold_custom_weights(self):
        """Buy and hold should work with custom weights."""
        data = create_sample_data()

        # 100% equity
        result = run_buy_and_hold(data, weights={"equity": 1.0, "bond": 0.0, "gold": 0.0, "cash": 0.0})

        assert len(result) == len(data)


class TestMetrics:
    """Tests for performance metrics."""

    def test_metrics_calculation(self):
        """Metrics should calculate without errors."""
        data = create_sample_data()
        result = run_backtest(data)
        metrics = calculate_metrics(result.portfolio_values)

        assert metrics.total_return is not None
        assert metrics.annualized_return is not None
        assert metrics.volatility >= 0
        assert -1 <= metrics.max_drawdown <= 0

    def test_win_rate_range(self):
        """Win rate should be between 0 and 1."""
        data = create_sample_data()
        result = run_backtest(data)
        metrics = calculate_metrics(result.portfolio_values)

        assert 0 <= metrics.win_rate <= 1

    def test_drawdown_series(self):
        """Drawdown should be non-positive."""
        data = create_sample_data()
        result = run_backtest(data)
        drawdown = calculate_drawdown_series(result.portfolio_values)

        assert all(drawdown["drawdown"] <= 0)
