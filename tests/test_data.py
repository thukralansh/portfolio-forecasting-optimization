from __future__ import annotations

import pandas as pd

from portfolio_forecasting.data import align_histories, fetch_price_history


def test_align_histories_intersects_dates() -> None:
    first = pd.DataFrame(
        {"price": [100.0, 101.0], "return": [0.01, 0.02]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )
    second = pd.DataFrame(
        {"price": [200.0, 202.0], "return": [0.03, 0.04]},
        index=pd.to_datetime(["2024-01-03", "2024-01-04"]),
    )

    aligned = align_histories({"AAA": first, "BBB": second})

    assert list(aligned["AAA"].index) == [pd.Timestamp("2024-01-03")]
    assert list(aligned["BBB"].index) == [pd.Timestamp("2024-01-03")]


def test_provider_failure_is_logged_with_traceback(monkeypatch, caplog):
    def unavailable(ticker):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("portfolio_forecasting.data.yf.Ticker", unavailable)
    assert fetch_price_history(["AAA"], "2020-01-01") == {}
    record = next(record for record in caplog.records if "AAA" in record.message)
    assert record.exc_info is not None
    assert "provider unavailable" in caplog.text
