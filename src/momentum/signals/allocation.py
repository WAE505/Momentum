"""Portfolio allocation based on momentum signals."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict

# Base allocation weights (when signals are fully positive)
BASE_WEIGHTS = {
    "equity": 0.70,
    "bond": 0.20,
    "gold": 0.10,
    "cash": 0.00,
}


@dataclass
class Allocation:
    """Portfolio allocation."""
    equity: float
    bond: float
    gold: float
    cash: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "equity": self.equity,
            "bond": self.bond,
            "gold": self.gold,
            "cash": self.cash,
        }

    def __post_init__(self):
        """Validate allocation sums to 1."""
        total = self.equity + self.bond + self.gold + self.cash
        if not np.isclose(total, 1.0, atol=0.001):
            raise ValueError(f"Allocation must sum to 1.0, got {total}")


def calculate_allocation(
    equity_signal: float,
    bond_signal: float,
    gold_signal: float
) -> Allocation:
    """
    Calculate portfolio allocation based on momentum signals.

    Uses hierarchical allocation:
    1. Gold gets its base weight × signal
    2. Equities get (base + unused gold) × signal
    3. Bonds get (base + unused equity) × signal
    4. Cash gets remainder

    Args:
        equity_signal: Equity momentum signal (0.0 to 1.0)
        bond_signal: Bond momentum signal (0.0 to 1.0)
        gold_signal: Gold momentum signal (0.0 to 1.0)

    Returns:
        Allocation object with weights for each asset
    """
    # Clamp signals to [0, 1]
    equity_signal = max(0.0, min(1.0, equity_signal))
    bond_signal = max(0.0, min(1.0, bond_signal))
    gold_signal = max(0.0, min(1.0, gold_signal))

    # Step 1: Gold allocation
    gold_weight = BASE_WEIGHTS["gold"] * gold_signal
    unused_gold = BASE_WEIGHTS["gold"] - gold_weight

    # Step 2: Equity allocation (base + unused gold)
    equity_available = BASE_WEIGHTS["equity"] + unused_gold
    equity_weight = equity_available * equity_signal
    unused_equity = equity_available - equity_weight

    # Step 3: Bond allocation (base + unused equity)
    bond_available = BASE_WEIGHTS["bond"] + unused_equity
    bond_weight = bond_available * bond_signal
    unused_bond = bond_available - bond_weight

    # Step 4: Cash gets the remainder
    cash_weight = unused_bond

    return Allocation(
        equity=equity_weight,
        bond=bond_weight,
        gold=gold_weight,
        cash=cash_weight,
    )


def calculate_allocations_series(signals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate allocations for a time series of signals.

    Args:
        signals_df: DataFrame with columns: date, equity_signal, bond_signal, gold_signal

    Returns:
        DataFrame with columns: date, equity_weight, bond_weight, gold_weight, cash_weight
    """
    allocations = []

    for _, row in signals_df.iterrows():
        alloc = calculate_allocation(
            row["equity_signal"],
            row["bond_signal"],
            row["gold_signal"]
        )
        allocations.append({
            "date": row["date"],
            "equity_weight": alloc.equity,
            "bond_weight": alloc.bond,
            "gold_weight": alloc.gold,
            "cash_weight": alloc.cash,
        })

    return pd.DataFrame(allocations)
