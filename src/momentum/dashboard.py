"""Streamlit dashboard for momentum strategy."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from momentum.data.cache import DataCache
from momentum.signals.momentum import calculate_all_signals
from momentum.signals.allocation import calculate_allocation
from momentum.backtest.engine import run_backtest, run_buy_and_hold
from momentum.backtest.metrics import (
    calculate_metrics,
    calculate_drawdown_series,
    compare_strategies,
)


st.set_page_config(
    page_title="Momentum Strategy Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("Momentum/Trend-Following Strategy Dashboard")
st.markdown("""
Based on the [ERN momentum strategy](https://earlyretirementnow.com/2025/11/12/momentum-trend-following-swr-series-part-63/).
Uses 12 momentum signals per asset with 8/9/10 month lookbacks.
""")


@st.cache_data(ttl=3600)
def load_data(start_date: str = "1988-01-01"):
    """Load market data with caching."""
    cache = DataCache()
    return cache.get_data(start_date=start_date)


@st.cache_data
def run_analysis(data: pd.DataFrame):
    """Run backtest and calculate metrics."""
    # Run momentum strategy
    result = run_backtest(data)

    # Run buy-and-hold benchmark
    benchmark = run_buy_and_hold(data)

    # Calculate metrics
    strategy_metrics = calculate_metrics(result.portfolio_values)
    benchmark_metrics = calculate_metrics(benchmark)

    return result, benchmark, strategy_metrics, benchmark_metrics


# Sidebar
with st.sidebar:
    st.header("Settings")

    # Date range
    start_year = st.slider("Start Year", 1990, 2020, 1990)
    start_date = f"{start_year}-01-01"

    # Refresh button
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**Data Sources**")
    st.markdown("- S&P 500: Yahoo Finance")
    st.markdown("- Treasuries: FRED")
    st.markdown("- Gold: Yahoo Finance")
    st.markdown("- T-Bills: FRED")


# Load data
try:
    with st.spinner("Loading market data..."):
        data = load_data(start_date)

    if data.empty:
        st.error("No data available. Please check your internet connection and try again.")
        st.stop()

    # Run analysis
    with st.spinner("Running backtest..."):
        result, benchmark, strategy_metrics, benchmark_metrics = run_analysis(data)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Please check your internet connection and try refreshing.")
    st.stop()


# Current Signals Section
st.header("Current Momentum Signals")

latest_signals = result.signals.iloc[-1]
latest_alloc = result.allocations.iloc[-1]

col1, col2, col3, col4 = st.columns(4)

def signal_color(signal: float) -> str:
    """Get color based on signal strength."""
    if signal >= 0.7:
        return "green"
    elif signal >= 0.4:
        return "orange"
    else:
        return "red"

def signal_emoji(signal: float) -> str:
    """Get emoji based on signal strength."""
    if signal >= 0.7:
        return "🟢"
    elif signal >= 0.4:
        return "🟡"
    else:
        return "🔴"

with col1:
    signal = latest_signals["equity_signal"]
    st.metric(
        "Equity Signal",
        f"{signal:.0%}",
        delta=f"{signal_emoji(signal)} {'Strong' if signal >= 0.7 else 'Neutral' if signal >= 0.4 else 'Weak'}"
    )

with col2:
    signal = latest_signals["bond_signal"]
    st.metric(
        "Bond Signal",
        f"{signal:.0%}",
        delta=f"{signal_emoji(signal)} {'Strong' if signal >= 0.7 else 'Neutral' if signal >= 0.4 else 'Weak'}"
    )

with col3:
    signal = latest_signals["gold_signal"]
    st.metric(
        "Gold Signal",
        f"{signal:.0%}",
        delta=f"{signal_emoji(signal)} {'Strong' if signal >= 0.7 else 'Neutral' if signal >= 0.4 else 'Weak'}"
    )

with col4:
    st.metric(
        "Last Updated",
        pd.to_datetime(latest_signals["date"]).strftime("%Y-%m-%d"),
    )


# Current Allocation
st.header("Recommended Allocation")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("**Current Weights:**")
    st.markdown(f"- Equity: **{latest_alloc['equity_weight']:.1%}**")
    st.markdown(f"- Bond: **{latest_alloc['bond_weight']:.1%}**")
    st.markdown(f"- Gold: **{latest_alloc['gold_weight']:.1%}**")
    st.markdown(f"- Cash: **{latest_alloc['cash_weight']:.1%}**")

with col2:
    # Pie chart
    fig = go.Figure(data=[go.Pie(
        labels=["Equity", "Bond", "Gold", "Cash"],
        values=[
            latest_alloc["equity_weight"],
            latest_alloc["bond_weight"],
            latest_alloc["gold_weight"],
            latest_alloc["cash_weight"],
        ],
        marker_colors=["#1f77b4", "#2ca02c", "#ffd700", "#7f7f7f"],
        hole=0.4,
    )])
    fig.update_layout(
        title="Current Allocation",
        height=300,
        margin=dict(t=50, b=0, l=0, r=0),
    )
    st.plotly_chart(fig, use_container_width=True)


# Performance Comparison
st.header("Historical Performance")

# Metrics comparison
col1, col2 = st.columns(2)

with col1:
    st.subheader("Momentum Strategy")
    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Total Return", f"{strategy_metrics.total_return:.1%}")
        st.metric("Volatility", f"{strategy_metrics.volatility:.1%}")
        st.metric("Max Drawdown", f"{strategy_metrics.max_drawdown:.1%}")
    with metrics_col2:
        st.metric("Annualized Return", f"{strategy_metrics.annualized_return:.1%}")
        st.metric("Sharpe Ratio", f"{strategy_metrics.sharpe_ratio:.2f}")
        st.metric("Win Rate", f"{strategy_metrics.win_rate:.1%}")

with col2:
    st.subheader("Buy & Hold (70/20/10)")
    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Total Return", f"{benchmark_metrics.total_return:.1%}")
        st.metric("Volatility", f"{benchmark_metrics.volatility:.1%}")
        st.metric("Max Drawdown", f"{benchmark_metrics.max_drawdown:.1%}")
    with metrics_col2:
        st.metric("Annualized Return", f"{benchmark_metrics.annualized_return:.1%}")
        st.metric("Sharpe Ratio", f"{benchmark_metrics.sharpe_ratio:.2f}")
        st.metric("Win Rate", f"{benchmark_metrics.win_rate:.1%}")


# Portfolio Value Chart
st.subheader("Portfolio Value Over Time")

# Combine data for chart
chart_data = result.portfolio_values[["date", "portfolio_value"]].copy()
chart_data = chart_data.rename(columns={"portfolio_value": "Momentum"})
chart_data["Buy & Hold"] = benchmark["portfolio_value"].values

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_data["date"],
    y=chart_data["Momentum"],
    name="Momentum Strategy",
    line=dict(color="#1f77b4"),
))
fig.add_trace(go.Scatter(
    x=chart_data["date"],
    y=chart_data["Buy & Hold"],
    name="Buy & Hold",
    line=dict(color="#ff7f0e", dash="dash"),
))
fig.update_layout(
    title="Portfolio Value ($100 initial investment)",
    xaxis_title="Date",
    yaxis_title="Portfolio Value ($)",
    yaxis_type="log",
    height=400,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
)
st.plotly_chart(fig, use_container_width=True)


# Drawdown Chart
st.subheader("Drawdown")

drawdown = calculate_drawdown_series(result.portfolio_values)
benchmark_dd = calculate_drawdown_series(benchmark)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=drawdown["date"],
    y=drawdown["drawdown"],
    name="Momentum Strategy",
    fill="tozeroy",
    line=dict(color="#1f77b4"),
))
fig.add_trace(go.Scatter(
    x=benchmark_dd["date"],
    y=benchmark_dd["drawdown"],
    name="Buy & Hold",
    line=dict(color="#ff7f0e", dash="dash"),
))
fig.update_layout(
    title="Drawdown from Peak",
    xaxis_title="Date",
    yaxis_title="Drawdown",
    yaxis_tickformat=".0%",
    height=300,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
)
st.plotly_chart(fig, use_container_width=True)


# Allocation Over Time
st.subheader("Allocation Over Time")

alloc_data = result.allocations.copy()
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=alloc_data["date"],
    y=alloc_data["equity_weight"],
    name="Equity",
    stackgroup="one",
    fillcolor="#1f77b4",
))
fig.add_trace(go.Scatter(
    x=alloc_data["date"],
    y=alloc_data["bond_weight"],
    name="Bond",
    stackgroup="one",
    fillcolor="#2ca02c",
))
fig.add_trace(go.Scatter(
    x=alloc_data["date"],
    y=alloc_data["gold_weight"],
    name="Gold",
    stackgroup="one",
    fillcolor="#ffd700",
))
fig.add_trace(go.Scatter(
    x=alloc_data["date"],
    y=alloc_data["cash_weight"],
    name="Cash",
    stackgroup="one",
    fillcolor="#7f7f7f",
))
fig.update_layout(
    title="Portfolio Allocation Over Time",
    xaxis_title="Date",
    yaxis_title="Allocation",
    yaxis_tickformat=".0%",
    height=300,
)
st.plotly_chart(fig, use_container_width=True)


# Signal History
with st.expander("Signal History"):
    signal_data = result.signals[["date", "equity_signal", "bond_signal", "gold_signal"]].copy()
    signal_data = signal_data.set_index("date")
    signal_data = signal_data.tail(24)  # Last 2 years

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=signal_data.index,
        y=signal_data["equity_signal"],
        name="Equity",
        mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=signal_data.index,
        y=signal_data["bond_signal"],
        name="Bond",
        mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=signal_data.index,
        y=signal_data["gold_signal"],
        name="Gold",
        mode="lines+markers",
    ))
    fig.update_layout(
        title="Momentum Signals (Last 24 Months)",
        xaxis_title="Date",
        yaxis_title="Signal Strength",
        yaxis_range=[0, 1],
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


# Raw Data
with st.expander("Raw Data"):
    tab1, tab2, tab3 = st.tabs(["Market Data", "Signals", "Allocations"])

    with tab1:
        st.dataframe(data.tail(24), use_container_width=True)

    with tab2:
        st.dataframe(
            result.signals[["date", "equity_signal", "bond_signal", "gold_signal"]].tail(24),
            use_container_width=True
        )

    with tab3:
        st.dataframe(result.allocations.tail(24), use_container_width=True)


# Footer
st.markdown("---")
st.markdown("""
**Disclaimer**: This is for educational purposes only. Past performance does not guarantee future results.
Always do your own research before making investment decisions.
""")
