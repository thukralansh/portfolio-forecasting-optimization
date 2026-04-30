"""Per-asset forecasting with Prophet."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from prophet import Prophet

logger = logging.getLogger(__name__)


def _build_prophet_frame(price_series: pd.Series) -> pd.DataFrame:
    """Convert a price series into Prophet's expected schema."""
    return pd.DataFrame({"ds": pd.to_datetime(price_series.index), "y": price_series.values})


def _future_business_dates(price_series: pd.Series, horizon_days: int) -> pd.DatetimeIndex:
    """Return the future business dates Prophet should forecast for."""
    if price_series.empty:
        raise ValueError("price_series must not be empty")

    last_date = pd.to_datetime(price_series.index[-1])
    return pd.bdate_range(start=last_date, periods=horizon_days + 1)[1:]


def forecast_target_date(price_series: pd.Series, horizon_days: int = 1) -> date:
    """Return the business date being forecast for."""
    return _future_business_dates(price_series, horizon_days=horizon_days)[-1].date()


def forecast_next_price(price_series: pd.Series, horizon_days: int = 1) -> float:
    """Fit Prophet to one asset's price series and forecast the next business day."""
    if price_series.empty:
        raise ValueError("price_series must not be empty")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
    )
    model.fit(_build_prophet_frame(price_series))

    future_dates = _future_business_dates(price_series, horizon_days=horizon_days)
    forecast = model.predict(pd.DataFrame({"ds": future_dates}))
    return float(forecast["yhat"].iloc[-1])


def forecast_portfolio(
    histories: dict[str, pd.DataFrame],
    horizon_days: int = 1,
) -> tuple[dict[str, float], dict[str, float]]:
    """Forecast next price and implied return for each ticker."""
    predictions: dict[str, float] = {}
    expected_returns: dict[str, float] = {}

    for ticker, history in histories.items():
        current_price = float(history["price"].iloc[-1])
        predicted_price = forecast_next_price(history["price"], horizon_days=horizon_days)
        predictions[ticker] = predicted_price
        expected_returns[ticker] = (predicted_price - current_price) / current_price
        logger.info(
            "Forecasted %s next price %.2f from current %.2f", ticker, predicted_price, current_price
        )

    return predictions, expected_returns
