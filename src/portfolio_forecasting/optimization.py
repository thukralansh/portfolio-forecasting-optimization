"""Portfolio optimization routines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def build_return_matrix(
    histories: dict[str, pd.DataFrame],
    lookback_days: int,
) -> pd.DataFrame:
    """Construct a historical return matrix over a recent trailing window."""
    data = {
        ticker: history["return"].tail(lookback_days).reset_index(drop=True)
        for ticker, history in histories.items()
    }
    return pd.DataFrame(data).dropna()


def optimize_weights(
    histories: dict[str, pd.DataFrame],
    expected_returns: dict[str, float],
    lookback_days: int,
    min_weight: float,
    max_weight: float,
    risk_aversion: float,
) -> dict[str, float]:
    """Solve a long-only mean-variance optimization problem."""
    tickers = list(expected_returns)
    if not tickers:
        raise ValueError("expected_returns must not be empty")

    return_matrix = build_return_matrix(histories, lookback_days=lookback_days)
    if return_matrix.empty:
        raise ValueError("Not enough historical data to build a return matrix")

    mu = np.array([expected_returns[ticker] for ticker in tickers], dtype=float)
    covariance = return_matrix[tickers].cov().to_numpy(dtype=float)
    asset_count = len(tickers)

    def objective(weights: np.ndarray) -> float:
        portfolio_return = float(weights @ mu)
        portfolio_variance = float(weights @ covariance @ weights)
        return -(portfolio_return - 0.5 * risk_aversion * portfolio_variance)

    bounds = tuple((min_weight, max_weight) for _ in range(asset_count))
    constraints = [{"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}]
    initial_guess = np.full(asset_count, 1.0 / asset_count)

    result = minimize(
        objective,
        initial_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    if not result.success:
        raise ValueError(f"Optimization failed: {result.message}")

    return {
        ticker: float(weight)
        for ticker, weight in zip(tickers, result.x, strict=True)
    }
