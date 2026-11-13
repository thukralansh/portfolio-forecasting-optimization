from __future__ import annotations

import pandas as pd
import pytest

from portfolio_forecasting.config import PortfolioConfig
from portfolio_forecasting.optimization import build_return_matrix, optimize_weights


def test_build_return_matrix_uses_recent_window() -> None:
    history = pd.DataFrame(
        {"return": [0.01, 0.02, 0.03], "price": [100.0, 101.0, 102.0]},
    )

    matrix = build_return_matrix({"AAA": history, "BBB": history}, lookback_days=2)

    assert len(matrix) == 2
    assert list(matrix.columns) == ["AAA", "BBB"]


def test_optimize_weights_returns_normalized_allocations() -> None:
    history_a = pd.DataFrame(
        {"return": [0.01, 0.00, 0.02, 0.01], "price": [100.0, 101.0, 100.0, 102.0]}
    )
    history_b = pd.DataFrame(
        {"return": [0.00, 0.01, 0.01, 0.00], "price": [90.0, 91.0, 92.0, 93.0]}
    )

    weights = optimize_weights(
        histories={"AAA": history_a, "BBB": history_b},
        expected_returns={"AAA": 0.02, "BBB": 0.01},
        lookback_days=4,
        min_weight=0.0,
        max_weight=1.0,
        risk_aversion=2.0,
    )

    assert set(weights) == {"AAA", "BBB"}
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_default_floor_and_reallocation_follow_expected_returns():
    config = PortfolioConfig()
    assert config.min_weight == 0.05
    history = pd.DataFrame({"return": [0.01, -0.01, 0.005, -0.005]})
    tickers = config.tickers

    def allocate(preferred):
        return optimize_weights(
            {ticker: history for ticker in tickers},
            {ticker: 0.10 if ticker == preferred else 0.0 for ticker in tickers},
            4,
            config.min_weight,
            config.max_weight,
            config.risk_aversion,
        )

    first, second = allocate(tickers[0]), allocate(tickers[1])
    for weights in (first, second):
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(0.05 - 1e-8 <= weight <= 0.45 + 1e-8 for weight in weights.values())
    assert first[tickers[0]] > second[tickers[0]]
    assert second[tickers[1]] > first[tickers[1]]


def test_optimizer_rejects_infeasible_bounds():
    history = pd.DataFrame({"return": [0.01, -0.01, 0.02]})
    with pytest.raises(ValueError, match="infeasible"):
        optimize_weights({"AAA": history}, {"AAA": 0.01}, 3, 0.05, 0.45, 5.0)
