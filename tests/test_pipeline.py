from unittest.mock import patch

import pandas as pd
import pytest

from portfolio_forecasting.config import PortfolioConfig
from portfolio_forecasting.pipeline import run_pipeline


def test_pipeline_does_not_silently_drop_a_configured_stock():
    history = pd.DataFrame({"price": [100.0, 101.0], "return": [0.01, 0.01]})
    with (
        patch("portfolio_forecasting.pipeline.fetch_price_history", return_value={"AAA": history}),
        pytest.raises(ValueError, match="missing price history: BBB"),
    ):
        run_pipeline(PortfolioConfig(tickers=["AAA", "BBB"]))
