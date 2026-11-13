"""Dashboard regression tests use fixed data, never database credentials."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from portfolio_forecasting.dashboard import _snapshot_table
from portfolio_forecasting.dashboard_charts import allocation_chart, error_chart, history_chart
from portfolio_forecasting.dashboard_data import compute_prediction_accuracy


def frames():
    forecasts = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "forecast_date": [date(2026, 5, 1)] * 2 + [date(2026, 5, 4)] * 2,
            "run_at": pd.to_datetime(["2026-04-30", "2026-04-30", "2026-05-01", "2026-05-01"]),
            "current_price": [100.0] * 4,
            "predicted_price": [110.0, 90.0, 120.0, 80.0],
            "expected_return": [0.1, -0.1, 0.2, -0.2],
            "weight": [0.45, 0.55, 0.45, 0.55],
        }
    )
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "price_date": [date(2026, 5, 1)] * 2,
            "close_price": [100.0, 100.0],
        }
    )
    return forecasts, prices, compute_prediction_accuracy(forecasts, prices)


def test_snapshot_percentages_scaled_once_without_mutating_data():
    forecasts, _, _ = frames()
    display = _snapshot_table(forecasts)
    assert display.iloc[0]["weight"] == 45.0
    assert display.iloc[0]["expected_return"] == 10.0
    assert forecasts.iloc[0]["weight"] == 0.45


def test_charts_show_actual_points_forecast_markers_and_symmetric_error_scale():
    forecasts, prices, accuracy = frames()
    figure = history_chart(forecasts, prices)
    assert figure.data[0].name == "Actual close"
    assert figure.data[0].mode == "lines+markers"
    assert figure.data[1].mode == "markers"
    assert figure.data[1].marker.symbol == "circle"
    assert figure.layout.yaxis.range[0] < 80
    assert figure.layout.yaxis.range[1] > 120
    errors = error_chart(accuracy)
    assert list(errors.data[0].y) == pytest.approx([0.1, -0.1])
    assert errors.layout.yaxis.range[0] == -errors.layout.yaxis.range[1]
    pie = allocation_chart(forecasts.iloc[:2])
    assert pie.data[0].type == "pie"
    assert list(pie.data[0].values) == [0.45, 0.55]
    assert pie.data[0].textinfo == "none"
    assert not pie.layout.annotations
    assert pie.layout.showlegend


def test_dashboard_renders_and_filters_ticker_date_and_percentages():
    with patch("portfolio_forecasting.dashboard.load_dashboard_frames", side_effect=frames):
        app = AppTest.from_string(
            "from portfolio_forecasting.dashboard import run_dashboard\nrun_dashboard()"
        ).run(timeout=20)
        assert not app.exception
        assert app.title[0].value == "Portfolio Forecasts"
        assert app.selectbox(key="ticker").value == "AAA"
        assert app.metric[3].value == "45.00%"
        assert app.metric[7].value == "10.00%"
        detail = app.dataframe[1].value
        assert list(detail["status"]) == ["Pending actual", "Evaluated"]
        assert detail.iloc[1]["error_pct"] == 10.0
        app.selectbox(key="ticker").select("BBB").run()
        assert not app.exception
        assert app.metric[2].value == "-20.00%"
        app.selectbox(key="target_date").select(date(2026, 5, 1)).run()
        assert not app.exception
        assert len(app.dataframe[1].value) == 1


def test_dashboard_empty_and_pending_actual_states():
    forecasts, prices, _ = frames()
    empty = pd.DataFrame()
    for data in [(empty, empty, empty), (forecasts, prices.iloc[:0], empty)]:
        with patch("portfolio_forecasting.dashboard.load_dashboard_frames", return_value=data):
            app = AppTest.from_string(
                "from portfolio_forecasting.dashboard import run_dashboard\nrun_dashboard()"
            ).run(timeout=20)
            assert not app.exception
            assert app.info
