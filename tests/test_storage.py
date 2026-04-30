from __future__ import annotations

from datetime import datetime, timezone

import pytest

from portfolio_forecasting.storage import build_forecast_rows, resolve_supabase_credentials


def test_resolve_supabase_credentials_prefers_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_example")
    monkeypatch.setenv("SUPABASE_KEY", "legacy_key")

    credentials = resolve_supabase_credentials()

    assert credentials == ("https://example.supabase.co", "sb_secret_example")


def test_resolve_supabase_credentials_requires_complete_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_example")

    with pytest.raises(ValueError):
        resolve_supabase_credentials()


def test_build_forecast_rows_returns_one_row_per_ticker() -> None:
    result = {
        "forecast_date": "2026-04-30",
        "tickers": ["AAA", "BBB"],
        "current_prices": {"AAA": 100.0, "BBB": 200.0},
        "predictions": {"AAA": 101.0, "BBB": 198.0},
        "expected_returns": {"AAA": 0.01, "BBB": -0.01},
        "weights": {"AAA": 0.6, "BBB": 0.4},
    }

    rows = build_forecast_rows(
        result,
        run_id="1234",
        run_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
    )

    assert len(rows) == 2
    assert rows[0]["forecast_date"] == "2026-04-30"
    assert rows[0]["run_id"] == "1234"
    assert rows[0]["ticker"] == "AAA"
    assert rows[1]["ticker"] == "BBB"
