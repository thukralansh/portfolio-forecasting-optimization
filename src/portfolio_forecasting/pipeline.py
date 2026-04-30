"""End-to-end portfolio forecasting pipeline."""

from __future__ import annotations

from typing import Any

from .config import PortfolioConfig
from .data import align_histories, fetch_price_history
from .forecasting import forecast_portfolio, forecast_target_date
from .optimization import optimize_weights


def run_pipeline(config: PortfolioConfig) -> dict[str, Any]:
    """Run the local forecasting and optimization workflow."""
    raw_histories = fetch_price_history(config.tickers, start_date=config.start_date)
    histories = align_histories(raw_histories)
    if not histories:
        raise ValueError("No aligned historical data available for the selected tickers")

    predictions, expected_returns = forecast_portfolio(
        histories,
        horizon_days=config.forecast_horizon_days,
    )
    weights = optimize_weights(
        histories=histories,
        expected_returns=expected_returns,
        lookback_days=config.lookback_days,
        min_weight=config.min_weight,
        max_weight=config.max_weight,
        risk_aversion=config.risk_aversion,
    )

    current_prices = {
        ticker: float(history["price"].iloc[-1])
        for ticker, history in histories.items()
    }
    reference_history = next(iter(histories.values()))
    forecast_date = forecast_target_date(
        reference_history["price"],
        horizon_days=config.forecast_horizon_days,
    )

    return {
        "forecast_date": forecast_date.isoformat(),
        "tickers": list(histories),
        "current_prices": current_prices,
        "predictions": predictions,
        "expected_returns": expected_returns,
        "weights": weights,
    }
