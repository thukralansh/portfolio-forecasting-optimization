"""Consistent, explicitly scaled Plotly figures for the research dashboard."""

import pandas as pd
import plotly.graph_objects as go

SURFACE = "#101516"
INK = "#edf2ee"
MUTED = "#a2ada8"
ACCENT = "#b9f568"
BLUE = "#70b7ff"
AMBER = "#ffbd69"


def _style(figure: go.Figure, height: int = 400) -> go.Figure:
    figure.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": INK, "family": "IBM Plex Sans, sans-serif", "size": 12},
        margin={"l": 24, "r": 24, "t": 55, "b": 35},
        legend={"orientation": "h", "y": 1.15, "x": 0},
        hovermode="x unified",
    )
    figure.update_xaxes(gridcolor="#26302e", zeroline=False, color=MUTED)
    figure.update_yaxes(gridcolor="#26302e", zeroline=False, color=MUTED)
    return figure


def allocation_chart(snapshot: pd.DataFrame) -> go.Figure:
    ordered = snapshot.sort_values("ticker")
    figure = go.Figure(
        go.Pie(
            labels=ordered["ticker"],
            values=ordered["weight"],
            hole=0.58,
            sort=False,
            textinfo="label+percent",
            textposition="outside",
            marker={
                "colors": [ACCENT, BLUE, AMBER, "#d78eab", "#5ac4ad", "#b5a4ee"],
                "line": {"color": SURFACE, "width": 3},
            },
            customdata=ordered[["expected_return"]],
            hovertemplate="%{label}<br>Allocation: %{value:.1%}<br>Expected return: "
            "%{customdata[0]:+.2%}<extra></extra>",
        )
    )
    _style(figure, 330)
    figure.update_layout(
        showlegend=False,
        annotations=[
            {
                "text": "ALLOCATION",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 12, "color": MUTED},
            }
        ],
    )
    return figure


def history_chart(forecasts: pd.DataFrame, prices: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    values = []
    if not prices.empty:
        prices = prices.sort_values("price_date")
        values.extend(prices["close_price"].dropna().tolist())
        figure.add_trace(
            go.Scatter(
                x=prices["price_date"],
                y=prices["close_price"],
                name="Actual close",
                mode="lines+markers",
                line={"color": BLUE, "width": 2},
                marker={"size": 3},
                hovertemplate="Actual: $%{y:,.2f}<extra></extra>",
            )
        )
    if not forecasts.empty:
        forecasts = forecasts.sort_values("forecast_date")
        values.extend(forecasts["predicted_price"].dropna().tolist())
        figure.add_trace(
            go.Scatter(
                x=forecasts["forecast_date"],
                y=forecasts["predicted_price"],
                name="Forecast target",
                mode="markers",
                marker={"color": AMBER, "size": 7, "symbol": "circle"},
                hovertemplate="Predicted: $%{y:,.2f}<extra></extra>",
            )
        )
    _style(figure, 430)
    figure.update_yaxes(title="Close price (USD)", tickprefix="$")
    if values:
        low, high = min(values), max(values)
        padding = max((high - low) * 0.12, abs(high) * 0.015, 1)
        figure.update_yaxes(range=[max(0, low - padding), high + padding])
    figure.update_xaxes(title="Target / trading date", hoverformat="%b %d, %Y")
    return figure


def error_chart(accuracy: pd.DataFrame) -> go.Figure:
    ordered = accuracy.sort_values("forecast_date")
    figure = go.Figure(
        go.Bar(
            x=ordered["forecast_date"],
            y=ordered["error_pct"],
            marker_color=[AMBER if value >= 0 else BLUE for value in ordered["error_pct"]],
            hovertemplate="%{x|%b %d, %Y}<br>Signed error: %{y:+.2%}<extra></extra>",
        )
    )
    _style(figure, 300)
    extent = max(0.01, float(ordered["error_pct"].abs().max()) * 1.15)
    figure.update_yaxes(title="Signed forecast error", tickformat=".1%", range=[-extent, extent])
    figure.update_xaxes(title="Evaluated target date")
    figure.add_hline(y=0, line_color=INK, line_width=1)
    return figure
