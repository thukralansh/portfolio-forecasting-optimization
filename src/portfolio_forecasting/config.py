"""Configuration defaults for the portfolio forecasting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PortfolioConfig:
    """Runtime configuration for the forecasting and optimization workflow."""

    tickers: list[str] = field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META"]
    )
    start_date: str = "2020-01-01"
    lookback_days: int = 252
    forecast_horizon_days: int = 1
    min_weight: float = 0.0
    max_weight: float = 0.45
    risk_aversion: float = 5.0
