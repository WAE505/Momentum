"""Signal calculation module."""

from .momentum import calculate_momentum_signals, calculate_combined_signal
from .allocation import calculate_allocation

__all__ = [
    "calculate_momentum_signals",
    "calculate_combined_signal",
    "calculate_allocation",
]
