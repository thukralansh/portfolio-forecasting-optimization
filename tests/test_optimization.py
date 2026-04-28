from __future__ import annotations

import pandas as pd

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
