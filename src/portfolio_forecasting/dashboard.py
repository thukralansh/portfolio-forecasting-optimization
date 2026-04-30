"""Streamlit dashboard for portfolio forecasts stored in Supabase."""

from __future__ import annotations

from datetime import date, timedelta

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_forecasting.dashboard_data import (
    compute_prediction_accuracy,
    load_asset_price_history,
    load_forecast_results,
)

st.set_page_config(page_title="Portfolio Forecast Dashboard", layout="wide")


def _inject_styles() -> None:
    """Add lightweight custom styling for a more intentional visual feel."""
    st.markdown(
        """
        <style>
          .stApp {
            background:
              radial-gradient(circle at top left, rgba(13, 110, 253, 0.10), transparent 30%),
              radial-gradient(circle at top right, rgba(25, 135, 84, 0.10), transparent 24%),
              linear-gradient(180deg, #f7f9fc 0%, #eef3f9 100%);
          }
          .hero {
            padding: 1.4rem 1.6rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0b2239 0%, #12395d 45%, #2b6f9f 100%);
            color: white;
            box-shadow: 0 18px 40px rgba(17, 35, 57, 0.18);
            margin-bottom: 1rem;
          }
          .hero h1 {
            margin: 0;
            font-size: 2.1rem;
            letter-spacing: -0.03em;
          }
          .hero p {
            margin: 0.4rem 0 0;
            color: rgba(255,255,255,0.85);
            font-size: 1rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)
def load_dashboard_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load forecast and actual price data, plus derived accuracy metrics."""
    forecasts = load_forecast_results()
    prices = load_asset_price_history()
    accuracy = compute_prediction_accuracy(forecasts, prices)
    return forecasts, prices, accuracy


def _render_header(latest_date: date | None) -> None:
    """Render the dashboard hero banner."""
    freshness = latest_date.isoformat() if latest_date is not None else "No runs yet"
    st.markdown(
        f"""
        <div class="hero">
          <h1>Portfolio Forecast Dashboard</h1>
          <p>Daily forecast snapshots, portfolio weights, and realized price history from Supabase.
          Latest forecast date: <strong>{freshness}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _weights_chart(run_df: pd.DataFrame):
    chart_df = run_df[["ticker", "weight"]].copy()
    if chart_df["weight"].sum() <= 0:
        return None

    fig = px.pie(
        chart_df,
        names="ticker",
        values="weight",
        hole=0.42,
        color_discrete_sequence=["#0d6efd", "#198754", "#fd7e14", "#dc3545", "#6f42c1", "#20c997"],
    )
    fig.update_traces(textinfo="label+percent", hovertemplate="%{label}: %{value:.2%}")
    fig.update_layout(showlegend=True, legend_title_text="Ticker", height=360)
    return fig


def _ticker_history_chart(
    ticker: str,
    forecasts: pd.DataFrame,
    actual_prices: pd.DataFrame,
    window_days: int,
):
    cutoff = date.today() - timedelta(days=window_days)
    actual_df = actual_prices[
        (actual_prices["ticker"] == ticker) & (actual_prices["price_date"] >= cutoff)
    ].copy()
    forecast_df = forecasts[
        (forecasts["ticker"] == ticker) & (forecasts["forecast_date"] >= cutoff)
    ].copy()

    if actual_df.empty and forecast_df.empty:
        return None

    actual_chart = (
        alt.Chart(actual_df)
        .mark_line(color="#0d6efd", strokeWidth=2.5)
        .encode(
            x=alt.X("price_date:T", title="Date"),
            y=alt.Y("close_price:Q", title="Price (USD)"),
            tooltip=[
                alt.Tooltip("price_date:T", title="Date"),
                alt.Tooltip("close_price:Q", title="Actual Close", format=".2f"),
            ],
        )
    )
    forecast_chart = (
        alt.Chart(forecast_df)
        .mark_line(color="#fd7e14", point=True, strokeDash=[6, 4], strokeWidth=2.5)
        .encode(
            x=alt.X("forecast_date:T", title="Date"),
            y=alt.Y("predicted_price:Q", title="Price (USD)"),
            tooltip=[
                alt.Tooltip("forecast_date:T", title="Forecast Date"),
                alt.Tooltip("predicted_price:Q", title="Predicted Price", format=".2f"),
            ],
        )
    )
    return alt.layer(actual_chart, forecast_chart).resolve_scale(y="shared")


def run_dashboard() -> None:
    """Render the dashboard."""
    _inject_styles()
    forecasts, prices, accuracy = load_dashboard_frames()
    latest_date = max(forecasts["forecast_date"]) if not forecasts.empty else None
    _render_header(latest_date)

    if forecasts.empty:
        st.info("No forecast rows are available yet. Run the live forecast pipeline first.")
        return

    available_dates = sorted(forecasts["forecast_date"].unique(), reverse=True)
    control_col, refresh_col = st.columns([5, 1])
    with control_col:
        selected_date = st.selectbox(
            "Forecast date",
            options=available_dates,
            format_func=lambda value: value.strftime("%Y-%m-%d"),
        )
    with refresh_col:
        st.write("")
        if st.button("Refresh"):
            st.cache_data.clear()
            st.rerun()

    run_df = forecasts[forecasts["forecast_date"] == selected_date].copy().sort_values("ticker")

    metric_one, metric_two, metric_three = st.columns(3)
    with metric_one:
        st.metric("Tickers in run", len(run_df))
    with metric_two:
        top_weight_row = run_df.sort_values("weight", ascending=False).iloc[0]
        st.metric("Top allocation", f"{top_weight_row['ticker']} · {top_weight_row['weight']:.1%}")
    with metric_three:
        st.metric("Average expected return", f"{run_df['expected_return'].mean():.2%}")

    left_col, right_col = st.columns([1.1, 1])
    with left_col:
        st.subheader("Portfolio Weights")
        weights_figure = _weights_chart(run_df)
        if weights_figure is None:
            st.info("No non-zero weights available for this run.")
        else:
            st.plotly_chart(weights_figure, use_container_width=True)

    with right_col:
        st.subheader("Forecast Snapshot")
        summary_df = run_df[["ticker", "current_price", "predicted_price", "expected_return", "weight"]]
        st.dataframe(
            summary_df.rename(
                columns={
                    "ticker": "Ticker",
                    "current_price": "Current Price",
                    "predicted_price": "Predicted Price",
                    "expected_return": "Expected Return",
                    "weight": "Weight",
                }
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                "Predicted Price": st.column_config.NumberColumn(format="$%.2f"),
                "Expected Return": st.column_config.NumberColumn(format="%.2f%%"),
                "Weight": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

    st.subheader("Ticker Detail")
    ticker_col, window_col = st.columns([2, 2])
    with ticker_col:
        selected_ticker = st.selectbox("Ticker", options=run_df["ticker"].tolist())
    with window_col:
        window_days = st.slider("History window (days)", min_value=30, max_value=730, value=180)

    ticker_row = run_df.set_index("ticker").loc[selected_ticker]
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("Current Price", f"${ticker_row['current_price']:.2f}")
    with d2:
        st.metric("Predicted Price", f"${ticker_row['predicted_price']:.2f}")
    with d3:
        st.metric("Expected Return", f"{ticker_row['expected_return']:.2%}")
    with d4:
        st.metric("Target Weight", f"{ticker_row['weight']:.2%}")

    history_chart = _ticker_history_chart(selected_ticker, forecasts, prices, window_days)
    st.subheader(f"Actual vs Predicted · {selected_ticker}")
    if history_chart is None:
        st.info("Not enough data yet to chart this ticker.")
    else:
        st.altair_chart(history_chart, use_container_width=True)
        st.caption(
            "Blue line shows actual closes from asset_price_history. Orange line shows forecasted closes by forecast date."
        )

    st.subheader("Prediction Accuracy")
    ticker_accuracy = accuracy[accuracy["ticker"] == selected_ticker].copy() if not accuracy.empty else pd.DataFrame()
    if ticker_accuracy.empty:
        st.info("Not enough realized history yet to calculate forecast accuracy for this ticker.")
    else:
        accuracy_chart = (
            alt.Chart(ticker_accuracy)
            .mark_bar(color="#12395d")
            .encode(
                x=alt.X("forecast_date:T", title="Forecast Date"),
                y=alt.Y("absolute_error:Q", title="Absolute Error (USD)"),
                tooltip=[
                    alt.Tooltip("forecast_date:T", title="Forecast Date"),
                    alt.Tooltip("predicted_price:Q", title="Predicted", format=".2f"),
                    alt.Tooltip("actual_close_price:Q", title="Actual", format=".2f"),
                    alt.Tooltip("absolute_error:Q", title="Absolute Error", format=".2f"),
                    alt.Tooltip("error_pct:Q", title="Error %", format=".2%"),
                ],
            )
        )
        st.altair_chart(accuracy_chart, use_container_width=True)
        st.dataframe(
            ticker_accuracy[
                [
                    "forecast_date",
                    "predicted_price",
                    "actual_close_price",
                    "error",
                    "absolute_error",
                    "error_pct",
                ]
            ].rename(
                columns={
                    "forecast_date": "Forecast Date",
                    "predicted_price": "Predicted Price",
                    "actual_close_price": "Actual Close",
                    "error": "Error",
                    "absolute_error": "Absolute Error",
                    "error_pct": "Error %",
                }
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Predicted Price": st.column_config.NumberColumn(format="$%.2f"),
                "Actual Close": st.column_config.NumberColumn(format="$%.2f"),
                "Error": st.column_config.NumberColumn(format="$%.2f"),
                "Absolute Error": st.column_config.NumberColumn(format="$%.2f"),
                "Error %": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )


def main() -> None:
    run_dashboard()


if __name__ == "__main__":
    main()
