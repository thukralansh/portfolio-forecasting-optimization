from __future__ import annotations

from datetime import date

import pandas as pd

from portfolio_forecasting.dashboard_data import compute_prediction_accuracy


def test_compute_prediction_accuracy_matches_forecast_date_to_actual_date() -> None:
    forecasts = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "forecast_date": [date(2026, 4, 30), date(2026, 5, 1), date(2026, 4, 30)],
            "predicted_price": [101.0, 103.0, 200.0],
        }
    )
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "price_date": [date(2026, 4, 30), date(2026, 5, 1), date(2026, 4, 30)],
            "close_price": [100.0, 104.0, 198.0],
        }
    )

    accuracy = compute_prediction_accuracy(forecasts, prices)

    assert len(accuracy) == 3
    assert accuracy.loc[0, "actual_close_price"] == 100.0
    assert accuracy.loc[0, "error"] == 1.0
    assert abs(float(accuracy.loc[2, "error_pct"]) - 2 / 198) < 1e-9


def test_accuracy_excludes_pending_and_invalid_prices_and_uses_actual_denominator():
    forecasts = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4,
            "forecast_date": [date(2026, 5, day) for day in range(1, 5)],
            "predicted_price": [110.0, 90.0, 100.0, 100.0],
            "current_price": [99.0] * 4,
        }
    )
    prices = pd.DataFrame(
        {
            "ticker": ["AAA"] * 3,
            "price_date": [date(2026, 5, day) for day in range(1, 4)],
            "close_price": [100.0, 0.0, float("nan")],
        }
    )
    result = compute_prediction_accuracy(forecasts, prices)
    assert len(result) == 1
    assert result.iloc[0]["error_pct"] == 0.1
    assert result.iloc[0]["baseline_absolute_error"] == 1.0
    assert result.iloc[0]["absolute_error_pct"] == 0.1


def test_accuracy_excludes_infinite_values():
    forecasts = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "forecast_date": [date(2026, 5, 1)] * 2,
            "predicted_price": [float("inf"), 100.0],
        }
    )
    actuals = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "price_date": [date(2026, 5, 1)] * 2,
            "close_price": [100.0, float("inf")],
        }
    )
    assert compute_prediction_accuracy(forecasts, actuals).empty
