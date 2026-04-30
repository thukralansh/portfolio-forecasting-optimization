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
    assert accuracy.loc[0, "error"] == -1.0
    assert round(float(accuracy.loc[2, "error_pct"]), 4) == -0.01
