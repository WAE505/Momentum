"""Tests for momentum signal calculations."""

import pytest
import pandas as pd
import numpy as np

from momentum.signals.momentum import (
    _sma_crossover_signal,
    _point_in_time_signal,
    calculate_momentum_signals,
    calculate_combined_signal,
)
from momentum.signals.allocation import calculate_allocation, Allocation


class TestSMACrossoverSignal:
    """Tests for SMA crossover signal."""

    def test_uptrend_signal(self):
        """Price above SMA should give signal of 1."""
        # Prices steadily increasing
        prices = pd.Series([100, 105, 110, 115, 120, 125, 130, 135, 140])
        signal = _sma_crossover_signal(prices, lookback=3)

        # After enough data, signal should be 1 (price above SMA)
        assert signal.iloc[-1] == 1

    def test_downtrend_signal(self):
        """Price below SMA should give signal of 0."""
        # Prices steadily decreasing
        prices = pd.Series([140, 135, 130, 125, 120, 115, 110, 105, 100])
        signal = _sma_crossover_signal(prices, lookback=3)

        # Signal should be 0 (price below SMA)
        assert signal.iloc[-1] == 0

    def test_early_values(self):
        """First few values before SMA is available should be 0 (no signal)."""
        prices = pd.Series([100, 110, 120, 130, 140])
        signal = _sma_crossover_signal(prices, lookback=3)

        # First 2 values are 0 because SMA comparison is False when SMA is NaN
        assert signal.iloc[0] == 0
        assert signal.iloc[1] == 0
        # After lookback period, signal should be valid
        assert signal.iloc[3] in [0, 1]


class TestPointInTimeSignal:
    """Tests for point-in-time signal."""

    def test_higher_price(self):
        """Current price higher than lookback should give signal of 1."""
        prices = pd.Series([100, 105, 110, 115, 120])
        signal = _point_in_time_signal(prices, lookback=2)

        # Price went from 110 to 120, so signal should be 1
        assert signal.iloc[-1] == 1

    def test_lower_price(self):
        """Current price lower than lookback should give signal of 0."""
        prices = pd.Series([120, 115, 110, 105, 100])
        signal = _point_in_time_signal(prices, lookback=2)

        # Price went from 110 to 100, so signal should be 0
        assert signal.iloc[-1] == 0


class TestMomentumSignals:
    """Tests for full momentum signal calculation."""

    def test_signal_count_equity(self):
        """Equity should have more signals due to avg2_sma variants."""
        prices = pd.Series([100 + i for i in range(20)])
        cash = pd.Series([100 + i * 0.01 for i in range(20)])

        signals = calculate_momentum_signals(prices, cash, "equity")

        # Equity has extra signals: avg2_sma for each lookback (3) + excess versions (3)
        # Base signals: sma_cross (3) + pit (3) + sma_cross_excess (3) + pit_excess (3) = 12
        # Plus avg2_sma (3) + avg2_sma_excess (3) = 6
        # Total = 18
        assert len(signals.columns) == 18

    def test_signal_count_bond(self):
        """Bond/gold should have 12 signals."""
        prices = pd.Series([100 + i for i in range(20)])
        cash = pd.Series([100 + i * 0.01 for i in range(20)])

        signals = calculate_momentum_signals(prices, cash, "bond")

        # sma_cross (3) + pit (3) + sma_cross_excess (3) + pit_excess (3) = 12
        assert len(signals.columns) == 12

    def test_combined_signal_range(self):
        """Combined signal should be between 0 and 1."""
        prices = pd.Series([100 + i for i in range(20)])
        cash = pd.Series([100 + i * 0.01 for i in range(20)])

        signals = calculate_momentum_signals(prices, cash, "equity")
        combined = calculate_combined_signal(signals)

        # All values should be between 0 and 1
        valid_values = combined.dropna()
        assert all(valid_values >= 0)
        assert all(valid_values <= 1)


class TestAllocation:
    """Tests for allocation calculation."""

    def test_full_signals_allocation(self):
        """Full signals (1.0) should give base weights."""
        alloc = calculate_allocation(1.0, 1.0, 1.0)

        assert np.isclose(alloc.equity, 0.70)
        assert np.isclose(alloc.bond, 0.20)
        assert np.isclose(alloc.gold, 0.10)
        assert np.isclose(alloc.cash, 0.00)

    def test_zero_signals_allocation(self):
        """Zero signals should put everything in cash."""
        alloc = calculate_allocation(0.0, 0.0, 0.0)

        assert np.isclose(alloc.equity, 0.00)
        assert np.isclose(alloc.bond, 0.00)
        assert np.isclose(alloc.gold, 0.00)
        assert np.isclose(alloc.cash, 1.00)

    def test_partial_signal_allocation(self):
        """Partial signals should cascade unused weight."""
        # Gold signal 0 -> gold weight 0, equity gets 70% + 10% = 80%
        # Equity signal 0.5 -> equity weight 40%, bond gets 20% + 40% = 60%
        # Bond signal 0.5 -> bond weight 30%, cash gets 30%
        alloc = calculate_allocation(0.5, 0.5, 0.0)

        assert np.isclose(alloc.gold, 0.00)
        assert np.isclose(alloc.equity, 0.40)
        assert np.isclose(alloc.bond, 0.30)
        assert np.isclose(alloc.cash, 0.30)

    def test_allocation_sums_to_one(self):
        """Allocation should always sum to 1."""
        for eq_sig in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for bond_sig in [0.0, 0.25, 0.5, 0.75, 1.0]:
                for gold_sig in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    alloc = calculate_allocation(eq_sig, bond_sig, gold_sig)
                    total = alloc.equity + alloc.bond + alloc.gold + alloc.cash
                    assert np.isclose(total, 1.0), f"Sum is {total} for signals {eq_sig}, {bond_sig}, {gold_sig}"

    def test_signal_clamping(self):
        """Signals outside [0,1] should be clamped."""
        # Test with out-of-range signals
        alloc = calculate_allocation(1.5, -0.5, 2.0)

        # Should be treated as 1.0, 0.0, 1.0
        total = alloc.equity + alloc.bond + alloc.gold + alloc.cash
        assert np.isclose(total, 1.0)
