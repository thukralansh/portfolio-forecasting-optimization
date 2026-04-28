"""Command-line entry point for local runs."""

from __future__ import annotations

import json
import logging

from .config import PortfolioConfig
from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    """Run the pipeline and print a compact JSON summary."""
    result = run_pipeline(PortfolioConfig())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
