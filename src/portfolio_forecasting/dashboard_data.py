"""Read-side helpers for the Streamlit dashboard."""

from __future__ import annotations

import os
from collections.abc import Callable

import pandas as pd
from supabase import Client, create_client

from portfolio_forecasting.storage import SUPABASE_URL_ENV

SUPABASE_PUBLISHABLE_KEY_ENV = "SUPABASE_PUBLISHABLE_KEY"
SUPABASE_PAGE_SIZE = 1000


def get_dashboard_supabase_client() -> Client:
    """Create a low-privilege Supabase client for the dashboard."""
    url = os.getenv(SUPABASE_URL_ENV)
    publishable_key = os.getenv(SUPABASE_PUBLISHABLE_KEY_ENV)
    if not url or not publishable_key:
        raise ValueError(
            "Dashboard access requires SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
        )
    return create_client(url, publishable_key)


def _fetch_all_rows(
    query_factory: Callable[[int, int], object],
    page_size: int = SUPABASE_PAGE_SIZE,
) -> list[dict[str, object]]:
    """Collect every row from a paginated Supabase query."""
    start = 0
    rows: list[dict[str, object]] = []

    while True:
        response = query_factory(start, start + page_size - 1).execute()
        data = getattr(response, "data", None) or []
        rows.extend(data)
        if len(data) < page_size:
            break
        start += page_size

    return rows


def load_forecast_results(client: Client | None = None) -> pd.DataFrame:
    """Load all forecast snapshots from Supabase."""
    supabase = client or get_dashboard_supabase_client()
    data = _fetch_all_rows(
        lambda start, end: (
            supabase.table("forecast_results")
            .select("*")
            .order("forecast_date", desc=False)
            .order("ticker", desc=False)
            .range(start, end)
        )
    )
    if not data:
        return pd.DataFrame()

    frame = pd.DataFrame(data)
    frame["forecast_date"] = pd.to_datetime(frame["forecast_date"]).dt.date
    frame["run_at"] = pd.to_datetime(frame["run_at"], utc=True).dt.tz_convert(None)
    numeric_columns = ["current_price", "predicted_price", "expected_return", "weight"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["forecast_date", "ticker"]).reset_index(drop=True)


def load_asset_price_history(client: Client | None = None) -> pd.DataFrame:
    """Load historical daily close prices from Supabase."""
    supabase = client or get_dashboard_supabase_client()
    data = _fetch_all_rows(
        lambda start, end: (
            supabase.table("asset_price_history")
            .select("*")
            .order("price_date", desc=False)
            .order("ticker", desc=False)
            .range(start, end)
        )
    )
    if not data:
        return pd.DataFrame()

    frame = pd.DataFrame(data)
    frame["price_date"] = pd.to_datetime(frame["price_date"]).dt.date
    frame["close_price"] = pd.to_numeric(frame["close_price"], errors="coerce")
    return frame.sort_values(["price_date", "ticker"]).reset_index(drop=True)


def compute_prediction_accuracy(
    forecast_results: pd.DataFrame,
    asset_price_history: pd.DataFrame,
) -> pd.DataFrame:
    """Compare each predicted price to the actual close on its forecast date."""
    if forecast_results.empty or asset_price_history.empty:
        return pd.DataFrame()

    actuals = asset_price_history.rename(
        columns={"price_date": "forecast_date", "close_price": "actual_close_price"}
    )
    merged = forecast_results.merge(
        actuals[["ticker", "forecast_date", "actual_close_price"]],
        on=["ticker", "forecast_date"],
        how="left",
    )
    merged = merged.dropna(subset=["actual_close_price"]).copy()
    if merged.empty:
        return merged

    merged["error"] = merged["actual_close_price"] - merged["predicted_price"]
    merged["absolute_error"] = merged["error"].abs()
    merged["error_pct"] = merged["error"] / merged["predicted_price"]
    return merged.sort_values(["ticker", "forecast_date"]).reset_index(drop=True)
