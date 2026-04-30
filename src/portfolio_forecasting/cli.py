"""Command-line entry point for local runs."""

from __future__ import annotations

import json
import logging

from .config import PortfolioConfig
from .pipeline import run_pipeline
from .storage import save_forecast_results_if_configured

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the pipeline, optionally persist results, and print a compact JSON summary."""
    result = run_pipeline(PortfolioConfig())
    if save_forecast_results_if_configured(result):
        logger.info("Persisted forecast results to Supabase")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
