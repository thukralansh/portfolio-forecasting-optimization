"""Read-only research dashboard for portfolio forecasts."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from portfolio_forecasting.dashboard_charts import allocation_chart, error_chart, history_chart
from portfolio_forecasting.dashboard_data import (
    compute_prediction_accuracy,
    load_asset_price_history,
    load_forecast_results,
)

st.set_page_config(page_title="Portfolio Forecasts", layout="wide")


def _inject_styles() -> None:
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    :root { --ink: #edf2ee; --muted: #a2ada8; --accent: #b9f568; --line: #293130; }
    .stApp, .stApp button, .stApp input, .stApp select,
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label {
        font-family: 'IBM Plex Sans', 'Trebuchet MS', sans-serif !important; }
    .stApp { background: #080a0b; color: var(--ink); }
    [data-testid="stHeader"] { background: #080a0b; }
    .block-container { max-width: 1380px; padding-top: 4.5rem; padding-bottom: 4rem; }
    h1, h2, h3 { font-family: 'IBM Plex Sans', 'Trebuchet MS', sans-serif;
        letter-spacing: -.035em; color: var(--ink); }
    h1 { font-size: clamp(2rem, 4vw, 3.4rem) !important; font-weight: 600 !important; }
    h2 { font-size: 1.5rem !important; margin-top: 1.5rem !important; }
    .eyebrow { font: 600 .75rem 'Menlo', monospace; color: var(--accent);
        letter-spacing: .18em; margin-bottom: .8rem; }
    .deck { color: var(--muted); max-width: 720px; margin-bottom: 1.5rem; }
    [data-testid="stMetric"] { border-top: 1px solid var(--line); padding: 1rem 0; }
    [data-testid="stMetricValue"] { font-family: 'Menlo', monospace;
        font-size: clamp(1.3rem, 2.4vw, 2rem); }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        color: var(--muted); }
    [data-testid="stSelectbox"] label { font-weight: 600; }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 3.5rem; font-size: 1.25rem; border-radius: 6px;
        background: #14191b; border-color: #39433d; color: var(--ink); }
    .stButton button { min-height: 3rem; border-radius: 6px; }
    .stButton button:hover { border-color: var(--accent); color: var(--accent); }
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
        border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    hr { border-color: var(--line); }
    .top-nav { display: flex; justify-content: space-between; align-items: center;
        gap: 1rem; border-bottom: 1px solid var(--line); padding-bottom: 1rem;
        margin-bottom: 2rem; flex-wrap: wrap; }
    .nav-brand { color: var(--ink); font-weight: 600; letter-spacing: .08em; }
    .nav-links { display: flex; gap: 1.25rem; flex-wrap: wrap; }
    .top-nav a { color: var(--muted); font-size: .85rem; text-decoration: none; }
    .top-nav a:hover, .top-nav a:focus-visible { color: var(--accent); }
    @media (max-width: 768px) { .block-container { padding: 4.5rem 1rem 3rem; } }
    @media (prefers-reduced-motion: no-preference) {
        .eyebrow { animation: reveal .5s ease-out; }
        @keyframes reveal { from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); } }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)
def load_dashboard_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    forecasts = load_forecast_results()
    prices = load_asset_price_history()
    return forecasts, prices, compute_prediction_accuracy(forecasts, prices)


def _snapshot_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert fractions to percentage points only in the display copy."""
    display = frame[
        ["ticker", "current_price", "predicted_price", "expected_return", "weight"]
    ].copy()
    display[["expected_return", "weight"]] *= 100
    return display


def _render_pending_targets(forecasts: pd.DataFrame) -> None:
    with st.expander("Inspect pending targets"):
        st.dataframe(
            forecasts[["forecast_date", "predicted_price"]].sort_values(
                "forecast_date", ascending=False
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "forecast_date": "Target date",
                "predicted_price": st.column_config.NumberColumn("Predicted close", format="$%.2f"),
            },
        )


def _render_analysis(accuracy: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    st.header("Forecast evaluation")
    st.caption(
        "Selected ticker and history window only. Each prediction is matched to the actual "
        "close on its target date. Missing actuals are pending, not zero-error predictions."
    )
    if accuracy.empty:
        st.info("No matching actual closes in this window yet. Accuracy is not available.")
        _render_pending_targets(forecasts)
        return

    mae = accuracy["absolute_error"].mean()
    rmse = (accuracy["error"].pow(2).mean()) ** 0.5
    mape = accuracy["absolute_error_pct"].mean()
    one, two, three, four = st.columns(4)
    one.metric("Evaluated targets", len(accuracy))
    two.metric("Mean absolute error", f"${mae:,.2f}")
    three.metric("Root mean square error", f"${rmse:,.2f}")
    four.metric("Mean absolute % error", f"{mape:.2%}")
    st.caption(
        "Lower is better. MAE is the typical dollar miss; RMSE emphasizes large misses. "
        "MAPE averages |prediction - actual| / actual. It is not an investment return or accuracy score."
    )
    if len(accuracy) < 20:
        st.info("Small evaluation sample: treat these metrics as preliminary.")

    st.plotly_chart(error_chart(accuracy), use_container_width=True, theme=None)
    st.caption(
        "Signed error = (predicted - actual) / actual. Above zero means overprediction; "
        "below zero means underprediction. The zero line is a perfect forecast."
    )
    paired = accuracy.dropna(subset=["baseline_absolute_error"])
    if not paired.empty:
        baseline_mae = paired["baseline_absolute_error"].mean()
        model_mae = paired["absolute_error"].mean()
        a, b = st.columns(2)
        a.metric("Model MAE · paired targets", f"${model_mae:,.2f}")
        b.metric("Last-close baseline MAE", f"${baseline_mae:,.2f}")
        st.caption(
            f"Compared on {len(paired)} identical targets. The baseline predicts no change from "
            "the stored reference price. A model is useful only if it improves on simple alternatives."
        )

    matched = forecasts.merge(
        accuracy[["ticker", "forecast_date", "actual_close_price", "error_pct"]],
        on=["ticker", "forecast_date"],
        how="left",
        validate="one_to_one",
    ).sort_values("forecast_date", ascending=False)
    matched["status"] = (
        matched["actual_close_price"].notna().map({True: "Evaluated", False: "Pending actual"})
    )
    matched["error_pct"] *= 100
    with st.expander("Inspect target-level results"):
        st.dataframe(
            matched[
                ["forecast_date", "predicted_price", "actual_close_price", "error_pct", "status"]
            ],
            hide_index=True,
            use_container_width=True,
            column_config={
                "forecast_date": "Target date",
                "predicted_price": st.column_config.NumberColumn("Predicted close", format="$%.2f"),
                "actual_close_price": st.column_config.NumberColumn("Actual close", format="$%.2f"),
                "error_pct": st.column_config.NumberColumn("Signed error", format="%.2f%%"),
                "status": "Evaluation status",
            },
        )


def run_dashboard() -> None:
    _inject_styles()
    st.markdown(
        '<nav class="top-nav" aria-label="Main navigation">'
        '<span class="nav-brand">PORTFOLIO LAB</span><div class="nav-links">'
        '<a href="#portfolio-forecasts" target="_self">Overview</a>'
        '<a href="#forecast-evaluation" target="_self">Evaluation</a>'
        '<a href="https://ansthukral.com" target="_blank" rel="noopener noreferrer">'
        "My website</a></div></nav>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow">PORTFOLIO / RESEARCH TERMINAL</div>', unsafe_allow_html=True)
    st.title("Portfolio Forecasts")
    st.markdown(
        '<div class="deck">Price forecasts, portfolio allocation, and model performance.</div>',
        unsafe_allow_html=True,
    )
    forecasts, prices, accuracy = load_dashboard_frames()
    if forecasts.empty:
        st.info("No forecasts available. Run the live forecasting pipeline first.")
        return

    ticker_col, date_col, refresh_col = st.columns([3, 2, 1])
    with date_col:
        selected_date = st.selectbox(
            "Forecast target date",
            sorted(forecasts["forecast_date"].unique(), reverse=True),
            key="target_date",
        )
    run_df = forecasts[forecasts["forecast_date"] == selected_date].sort_values("ticker").copy()
    with ticker_col:
        ticker = st.selectbox("Explore a stock", run_df["ticker"].tolist(), key="ticker")
    with refresh_col:
        st.write("")
        if st.button("Refresh data", use_container_width=True):
            load_dashboard_frames.clear()
            st.rerun()

    latest_run = pd.to_datetime(forecasts["run_at"], utc=True).max()
    latest_actual = prices["price_date"].max() if not prices.empty else None
    st.caption(
        f"Latest run: {latest_run:%Y-%m-%d %H:%M UTC} | Latest actual close: {latest_actual}"
    )
    if (pd.Timestamp.now(tz="UTC") - latest_run).total_seconds() > 4 * 86400:
        st.warning(
            "Data is stale: no forecast run in over four days. Check the scheduled pipeline."
        )

    row = run_df.set_index("ticker").loc[ticker]
    st.header(f"{ticker} / Price outlook")
    one, two, three, four = st.columns(4)
    one.metric("Reference price", f"${row['current_price']:,.2f}")
    two.metric("Predicted close", f"${row['predicted_price']:,.2f}")
    three.metric("Expected return", f"{row['expected_return']:+.2%}")
    four.metric("Stored allocation", f"{row['weight']:.2%}")
    window_days = st.select_slider(
        "History window",
        options=[30, 90, 180, 365, 730],
        value=180,
        format_func=lambda days: f"{days} days",
    )
    cutoff = selected_date - timedelta(days=window_days)
    ticker_forecasts = forecasts[
        (forecasts["ticker"] == ticker)
        & (forecasts["forecast_date"] >= cutoff)
        & (forecasts["forecast_date"] <= selected_date)
    ].copy()
    ticker_prices = (
        prices[
            (prices["ticker"] == ticker)
            & (prices["price_date"] >= cutoff)
            & (prices["price_date"] <= selected_date)
        ].copy()
        if not prices.empty
        else prices
    )
    st.plotly_chart(
        history_chart(ticker_forecasts, ticker_prices), use_container_width=True, theme=None
    )
    st.caption(
        "Solid blue: actual daily closes. Amber markers: independent forecasts at their target dates, "
        "not a simulated trading path. Historical selections use today's available actuals; "
        "this is retrospective evaluation, not a point-in-time backtest."
    )

    st.header("Portfolio positioning")
    weighted_return = (run_df["weight"] * run_df["expected_return"]).sum()
    st.caption(
        f"Allocation-weighted expected return: {weighted_return:+.2%}. "
        "Model estimate, not guaranteed performance."
    )
    chart_col, table_col = st.columns([1, 1.6])
    with chart_col:
        st.plotly_chart(allocation_chart(run_df), use_container_width=True, theme=None)
    with table_col:
        st.dataframe(
            _snapshot_table(run_df),
            hide_index=True,
            use_container_width=True,
            column_config={
                "ticker": "Stock",
                "current_price": st.column_config.NumberColumn("Reference", format="$%.2f"),
                "predicted_price": st.column_config.NumberColumn("Forecast", format="$%.2f"),
                "expected_return": st.column_config.NumberColumn(
                    "Expected return", format="%.2f%%"
                ),
                "weight": st.column_config.NumberColumn("Allocation", format="%.2f%%"),
            },
        )
        st.caption(
            "New pipeline runs use a 5% floor and 45% cap per available stock. "
            "Weights maximize expected return minus a historical-risk penalty. "
            "Older snapshots retain their original allocations; nothing is rewritten."
        )
        if (run_df["weight"] < 0.05 - 1e-8).any():
            st.info("This snapshot predates the 5% allocation floor.")

    ticker_accuracy = (
        accuracy[
            (accuracy["ticker"] == ticker)
            & (accuracy["forecast_date"] >= cutoff)
            & (accuracy["forecast_date"] <= selected_date)
        ].copy()
        if not accuracy.empty
        else accuracy
    )
    _render_analysis(ticker_accuracy, ticker_forecasts)
    st.divider()
    st.caption(
        "Research only. Forecasts can be materially wrong. No trading is performed. "
        "Business-day targets may include exchange holidays."
    )


def main() -> None:
    run_dashboard()


if __name__ == "__main__":
    main()
