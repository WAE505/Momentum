"""Backtesting engine for momentum strategy."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

from ..signals.momentum import calculate_all_signals
from ..signals.allocation import calculate_allocation

# Expense ratios (annual, applied monthly)
EXPENSE_RATIOS = {
    "equity": 0.0003,  # 0.03%
    "bond": 0.0015,    # 0.15%
    "gold": 0.0009,    # 0.09%
    "cash": 0.0009,    # 0.09%
}

# Transaction cost per rebalance
TRANSACTION_COST = 0.0003  # 0.03%


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    portfolio_values: pd.DataFrame
    allocations: pd.DataFrame
    signals: pd.DataFrame
    trades: pd.DataFrame


def run_backtest(
    data: pd.DataFrame,
    initial_value: float = 100.0,
    apply_costs: bool = True,
    rebalance_threshold: float = 0.0
) -> BacktestResult:
    """
    Run backtest of momentum strategy.

    Args:
        data: DataFrame with columns: date, equity, bond, gold, cash
        initial_value: Starting portfolio value
        apply_costs: Whether to apply expense ratios and transaction costs
        rebalance_threshold: Minimum weight change to trigger rebalance (0 = always rebalance)

    Returns:
        BacktestResult with portfolio values, allocations, and signals
    """
    data = data.copy()
    data = data.sort_values("date").reset_index(drop=True)

    # Calculate signals
    signals = calculate_all_signals(data)

    # Initialize tracking
    portfolio_value = initial_value
    current_weights = {"equity": 0.0, "bond": 0.0, "gold": 0.0, "cash": 1.0}

    portfolio_values = []
    allocations = []
    trades = []

    # Calculate returns for each asset
    data = data.set_index("date")
    returns = data[["equity", "bond", "gold", "cash"]].pct_change()
    returns = returns.fillna(0)

    signals = signals.set_index("date")

    for i, date in enumerate(data.index):
        if i == 0:
            # First period: just record initial state
            portfolio_values.append({
                "date": date,
                "portfolio_value": portfolio_value,
                "equity_value": 0,
                "bond_value": 0,
                "gold_value": 0,
                "cash_value": portfolio_value,
            })
            allocations.append({
                "date": date,
                "equity_weight": 0,
                "bond_weight": 0,
                "gold_weight": 0,
                "cash_weight": 1.0,
            })
            continue

        # Get returns for this period
        period_returns = returns.loc[date]

        # Apply returns to current holdings
        new_values = {}
        for asset in ["equity", "bond", "gold", "cash"]:
            asset_value = portfolio_value * current_weights[asset]
            asset_return = period_returns[asset]

            # Apply expense ratio (monthly = annual / 12)
            if apply_costs:
                expense = EXPENSE_RATIOS[asset] / 12
                asset_return -= expense

            new_values[asset] = asset_value * (1 + asset_return)

        portfolio_value = sum(new_values.values())

        # Update current weights based on drift
        for asset in current_weights:
            current_weights[asset] = new_values[asset] / portfolio_value if portfolio_value > 0 else 0

        # Get target allocation from signals
        row = signals.loc[date]
        target_alloc = calculate_allocation(
            row["equity_signal"],
            row["bond_signal"],
            row["gold_signal"]
        )
        target_weights = target_alloc.to_dict()

        # Check if rebalancing is needed
        weight_changes = {
            asset: abs(target_weights[asset] - current_weights[asset])
            for asset in current_weights
        }
        max_change = max(weight_changes.values())

        if max_change > rebalance_threshold:
            # Apply transaction costs
            if apply_costs:
                total_turnover = sum(weight_changes.values()) / 2  # One-way turnover
                transaction_cost = total_turnover * TRANSACTION_COST
                portfolio_value *= (1 - transaction_cost)

            # Record trade
            trades.append({
                "date": date,
                "turnover": sum(weight_changes.values()) / 2,
                **{f"{asset}_change": target_weights[asset] - current_weights[asset]
                   for asset in current_weights}
            })

            # Rebalance to target weights
            current_weights = target_weights.copy()

        # Record portfolio state
        portfolio_values.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "equity_value": portfolio_value * current_weights["equity"],
            "bond_value": portfolio_value * current_weights["bond"],
            "gold_value": portfolio_value * current_weights["gold"],
            "cash_value": portfolio_value * current_weights["cash"],
        })

        allocations.append({
            "date": date,
            "equity_weight": current_weights["equity"],
            "bond_weight": current_weights["bond"],
            "gold_weight": current_weights["gold"],
            "cash_weight": current_weights["cash"],
            "equity_signal": row["equity_signal"],
            "bond_signal": row["bond_signal"],
            "gold_signal": row["gold_signal"],
        })

    return BacktestResult(
        portfolio_values=pd.DataFrame(portfolio_values),
        allocations=pd.DataFrame(allocations),
        signals=signals.reset_index(),
        trades=pd.DataFrame(trades) if trades else pd.DataFrame(),
    )


def run_buy_and_hold(
    data: pd.DataFrame,
    weights: dict = None,
    initial_value: float = 100.0,
    apply_costs: bool = True
) -> pd.DataFrame:
    """
    Run buy-and-hold strategy for comparison.

    Args:
        data: DataFrame with columns: date, equity, bond, gold, cash
        weights: Asset weights (default: 70/20/10/0)
        initial_value: Starting portfolio value
        apply_costs: Whether to apply expense ratios

    Returns:
        DataFrame with portfolio values over time
    """
    if weights is None:
        weights = {"equity": 0.70, "bond": 0.20, "gold": 0.10, "cash": 0.0}

    data = data.copy()
    data = data.sort_values("date").reset_index(drop=True)
    data = data.set_index("date")

    returns = data[["equity", "bond", "gold", "cash"]].pct_change()
    returns = returns.fillna(0)

    portfolio_value = initial_value
    portfolio_values = []

    for i, date in enumerate(data.index):
        if i == 0:
            portfolio_values.append({
                "date": date,
                "portfolio_value": portfolio_value,
            })
            continue

        # Apply returns
        period_returns = returns.loc[date]
        portfolio_return = 0

        for asset in weights:
            asset_return = period_returns[asset]
            if apply_costs:
                asset_return -= EXPENSE_RATIOS[asset] / 12
            portfolio_return += weights[asset] * asset_return

        portfolio_value *= (1 + portfolio_return)

        portfolio_values.append({
            "date": date,
            "portfolio_value": portfolio_value,
        })

    return pd.DataFrame(portfolio_values)
