.PHONY: install install-dev lint test run dashboard clean

PYTHON := ./.venv/bin/python
PIP := ./.venv/bin/pip

install:
	python3 -m venv .venv
	$(PIP) install -e .

install-dev:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests

test:
	$(PYTHON) -m pytest -q

run:
	$(PYTHON) -m portfolio_forecasting.cli

dashboard:
	$(PYTHON) -m streamlit run src/portfolio_forecasting/dashboard.py

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
