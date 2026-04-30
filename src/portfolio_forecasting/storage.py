"""Persistence helpers for saving forecast results to Supabase."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

logger = logging.getLogger(__name__)

SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_SECRET_KEY_ENV = "SUPABASE_SECRET_KEY"
SUPABASE_LEGACY_KEY_ENV = "SUPABASE_KEY"
FORECAST_RESULTS_TABLE = "forecast_results"


def resolve_supabase_credentials(optional: bool = False) -> tuple[str, str] | None:
    """Return Supabase credentials from the environment."""
    url = os.getenv(SUPABASE_URL_ENV)
    key = os.getenv(SUPABASE_SECRET_KEY_ENV) or os.getenv(SUPABASE_LEGACY_KEY_ENV)

    if optional and not url and not key:
        return None

    if not url or not key:
        raise ValueError(
            "Supabase persistence requires SUPABASE_URL and SUPABASE_SECRET_KEY "
            "(or legacy SUPABASE_KEY)."
        )

    return url, key


def get_supabase_client(optional: bool = False) -> Client | None:
    """Create a Supabase client from environment variables."""
    credentials = resolve_supabase_credentials(optional=optional)
    if credentials is None:
        return None

    url, key = credentials
    return create_client(url, key)


def build_forecast_rows(
    result: dict[str, Any],
    *,
    run_id: str | None = None,
    run_at: datetime | None = None,
) -> list[dict[str, object]]:
    """Transform pipeline output into rows for the forecast_results table."""
    forecast_date = result["forecast_date"]
    tickers = result["tickers"]
    current_prices = result["current_prices"]
    predictions = result["predictions"]
    expected_returns = result["expected_returns"]
    weights = result["weights"]

    resolved_run_id = run_id or str(uuid4())
    resolved_run_at = (run_at or datetime.now(timezone.utc)).isoformat()

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        rows.append(
            {
                "run_id": resolved_run_id,
                "run_at": resolved_run_at,
                "forecast_date": forecast_date,
                "ticker": ticker,
                "current_price": float(current_prices[ticker]),
                "predicted_price": float(predictions[ticker]),
                "expected_return": float(expected_returns[ticker]),
                "weight": float(weights[ticker]),
            }
        )

    return rows


def save_forecast_results(result: dict[str, Any], client: Client | None = None) -> int:
    """Upsert one forecast row per ticker into Supabase."""
    supabase = client or get_supabase_client(optional=False)
    if supabase is None:  # pragma: no cover - guarded by resolve_supabase_credentials()
        raise ValueError("Supabase client could not be created")

    rows = build_forecast_rows(result)
    supabase.table(FORECAST_RESULTS_TABLE).upsert(
        rows,
        on_conflict="forecast_date,ticker",
    ).execute()
    logger.info(
        "Saved %s forecast rows to Supabase for forecast_date=%s",
        len(rows),
        result["forecast_date"],
    )
    return len(rows)


def save_forecast_results_if_configured(result: dict[str, Any]) -> bool:
    """Persist results only when Supabase credentials are present."""
    supabase = get_supabase_client(optional=True)
    if supabase is None:
        logger.info("Supabase credentials not configured locally; skipping persistence")
        return False

    save_forecast_results(result, client=supabase)
    return True
