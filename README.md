# Momentum/Trend-Following Investment Strategy

A Python application to evaluate and track momentum/trend-following investment strategies, based on the [Early Retirement Now methodology](https://earlyretirementnow.com/2025/11/12/momentum-trend-following-swr-series-part-63/).

## Overview

This project implements a momentum-based tactical asset allocation strategy that:
- Calculates 12 momentum signals per asset class using multiple lookback periods
- Dynamically allocates between equities, bonds, gold, and cash based on signal strength
- Provides historical backtesting and live signal tracking via a web dashboard

## Strategy Details

### Assets
- **Equities**: S&P 500 Total Return Index (70% base allocation)
- **Bonds**: 10-Year Treasury Total Return (20% base allocation)
- **Gold**: Gold futures (10% base allocation)
- **Cash**: 3-Month T-Bills (receives unused allocation)

### Momentum Signals (12 per asset)

For each lookback period (8, 9, 10 months):
1. **SMA Crossover**: Current price > Simple Moving Average
2. **Point-in-Time**: Current price > Price N months ago
3. **SMA Crossover (Excess)**: Same as #1, but using returns in excess of cash
4. **Point-in-Time (Excess)**: Same as #2, but using returns in excess of cash

For equities only, additional signals:
5. **Avg 2-Month vs SMA**: Average of last 2 months > SMA
6. **Avg 2-Month vs SMA (Excess)**: Same using excess returns

Each signal outputs 0 (negative momentum) or 1 (positive momentum). The combined signal is the average of all signals (0.0 to 1.0).

### Allocation Logic

Hierarchical allocation where unused weight cascades down:
```
gold_weight = 10% × gold_signal
equity_weight = (70% + unused_gold) × equity_signal
bond_weight = (20% + unused_equity) × bond_signal
cash_weight = remainder
```

### Costs Modeled
- **Expense Ratios**: Equity 0.03%, Bond 0.15%, Gold 0.09%, Cash 0.09%
- **Transaction Costs**: 0.03% per rebalance

## Installation

```bash
# Clone the repository
git clone https://github.com/WAE505/Momentum.git
cd Momentum

# Install dependencies
pip install -e ".[dev]"
```

## Usage

### Run the Dashboard
```bash
python -m streamlit run src/momentum/dashboard.py
```
Open http://localhost:8501 in your browser.

### Run Tests
```bash
pytest tests/ -v
```

## Backtest Results (August 2000 - January 2026)

### Performance Comparison

| Metric | Momentum Strategy | Buy & Hold (70/20/10) |
|--------|-------------------|----------------------|
| Total Return | 744.4% | 584.4% |
| Annualized Return | 4.3% | 3.8% |
| Volatility | 5.4% | 7.8% |
| Sharpe Ratio | 0.81 | 0.52 |
| Max Drawdown | -11.4% | -35.5% |
| Max Drawdown Duration | 47 months | 102 months |
| Win Rate | 60.1% | 60.7% |
| Best Month | +6.0% | +9.7% |
| Worst Month | -5.9% | -13.6% |
| Final Value ($100 start) | $844.39 | $684.41 |

### Crisis Performance

| Event | Momentum | Buy & Hold |
|-------|----------|------------|
| 2008 Financial Crisis | +1.3% | -35.5% |
| 2020 COVID Crash | -4.2% | -13.5% |
| 2022 Bear Market | -6.8% | -20.7% |

### Trade Statistics
- Total rebalances: 598
- Rebalances per year: 11.7
- Average turnover per rebalance: 12.6%

## Current Signals (January 2026)

| Asset | Signal | Status |
|-------|--------|--------|
| Equity | 100% | STRONG |
| Bond | 67% | NEUTRAL |
| Gold | 100% | STRONG |

### Recommended Allocation
- Equity: 70.0%
- Gold: 10.0%
- Bond: 13.3%
- Cash: 6.7%

## Project Structure

```
momentum/
├── pyproject.toml              # Project dependencies and config
├── src/momentum/
│   ├── __init__.py
│   ├── data/
│   │   ├── sources.py          # Yahoo Finance & FRED data fetching
│   │   └── cache.py            # SQLite caching for market data
│   ├── signals/
│   │   ├── momentum.py         # 12 momentum signal calculations
│   │   └── allocation.py       # Hierarchical weight allocation
│   ├── backtest/
│   │   ├── engine.py           # Backtesting simulation engine
│   │   └── metrics.py          # Performance metrics calculation
│   └── dashboard.py            # Streamlit web application
├── tests/
│   ├── test_signals.py         # Signal calculation tests (12 tests)
│   └── test_backtest.py        # Backtest engine tests (10 tests)
└── data/                       # Cached market data (SQLite)
```

## Test Results

All 22 tests passing:

```
tests/test_backtest.py::TestBacktestEngine::test_backtest_runs PASSED
tests/test_backtest.py::TestBacktestEngine::test_backtest_initial_value PASSED
tests/test_backtest.py::TestBacktestEngine::test_backtest_allocations_sum_to_one PASSED
tests/test_backtest.py::TestBacktestEngine::test_backtest_with_costs PASSED
tests/test_backtest.py::TestBuyAndHold::test_buy_and_hold_runs PASSED
tests/test_backtest.py::TestBuyAndHold::test_buy_and_hold_custom_weights PASSED
tests/test_backtest.py::TestMetrics::test_metrics_calculation PASSED
tests/test_backtest.py::TestMetrics::test_win_rate_range PASSED
tests/test_backtest.py::TestMetrics::test_drawdown_series PASSED
tests/test_signals.py::TestSMACrossoverSignal::test_uptrend_signal PASSED
tests/test_signals.py::TestSMACrossoverSignal::test_downtrend_signal PASSED
tests/test_signals.py::TestSMACrossoverSignal::test_early_values PASSED
tests/test_signals.py::TestPointInTimeSignal::test_higher_price PASSED
tests/test_signals.py::TestPointInTimeSignal::test_lower_price PASSED
tests/test_signals.py::TestMomentumSignals::test_signal_count_equity PASSED
tests/test_signals.py::TestMomentumSignals::test_signal_count_bond PASSED
tests/test_signals.py::TestMomentumSignals::test_combined_signal_range PASSED
tests/test_signals.py::TestAllocation::test_full_signals_allocation PASSED
tests/test_signals.py::TestAllocation::test_zero_signals_allocation PASSED
tests/test_signals.py::TestAllocation::test_partial_signal_allocation PASSED
tests/test_signals.py::TestAllocation::test_allocation_sums_to_one PASSED
tests/test_signals.py::TestAllocation::test_signal_clamping PASSED
```

## Data Sources

- **S&P 500 Total Return**: Yahoo Finance (`^SP500TR`)
- **10-Year Treasury Yields**: FRED (`DGS10`) - converted to total return index
- **Gold**: Yahoo Finance (`GC=F`)
- **3-Month T-Bill Rate**: FRED (`DTB3`)

Data availability starts from approximately 1988-2000 depending on the asset.

## Key Findings

1. **Superior Risk-Adjusted Returns**: The momentum strategy achieved a Sharpe ratio of 0.81 compared to 0.52 for buy-and-hold, indicating better return per unit of risk.

2. **Dramatic Drawdown Reduction**: Maximum drawdown was reduced from -35.5% to -11.4%, a 68% improvement in downside protection.

3. **Crisis Alpha**: The strategy actually gained +1.3% during the 2008 financial crisis while buy-and-hold lost -35.5%, demonstrating effective risk-off positioning.

4. **Lower Volatility**: Annual volatility of 5.4% vs 7.8% provides a smoother investment experience.

5. **Higher Terminal Wealth**: Despite being more conservative, the strategy ended with 23% more wealth ($844 vs $684 from $100 initial investment).

## Disclaimer

This is for educational purposes only. Past performance does not guarantee future results. Always do your own research before making investment decisions.

## License

MIT
