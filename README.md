# Portfolio Forecasting & Optimization

A clean-room implementation of a portfolio research workflow that:

- downloads historical asset prices,
- forecasts next-session prices with Prophet,
- converts those forecasts into expected returns, and
- solves a constrained mean-variance allocation problem.

This version now includes:

- a scheduled forecasting pipeline that writes to Supabase, and
- a Streamlit dashboard that reads from Supabase using a publishable key plus RLS policies.

## What It Does

The pipeline runs in four stages:

1. Fetch adjusted close prices for a list of tickers.
2. Align historical returns across the portfolio universe.
3. Fit a separate Prophet model per asset and estimate one-step-ahead returns.
4. Optimize portfolio weights using a long-only mean-variance objective.

## Project Layout

```text
src/portfolio_forecasting/
  config.py
  data.py
  forecasting.py
  optimization.py
  pipeline.py
  cli.py
  dashboard_data.py
  dashboard.py
tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m portfolio_forecasting.cli
```

If `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are set in the environment, the CLI will also
upsert one row per ticker into the `forecast_results` table and sync historical daily prices
into the `asset_price_history` table for richer dashboard visualizations.

## Dashboard

The Streamlit dashboard reads from Supabase using:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`

Run it locally with:

```bash
make dashboard
```

### Supabase read policies

Because the dashboard uses a publishable key, both tables need `SELECT` policies for the
`anon` role. In Supabase SQL Editor, run:

```sql
create policy "public read forecast results"
on public.forecast_results
for select
to anon
using (true);

create policy "public read asset price history"
on public.asset_price_history
for select
to anon
using (true);
```

If you also want authenticated users to read through the same path, add matching `to authenticated`
policies as well.

## Customize

Edit the defaults in `src/portfolio_forecasting/config.py` to change:

- ticker universe
- start date
- lookback window
- minimum and maximum asset weights
- risk aversion

## Notes

- This project is for research and learning purposes only.
- Forecasts and allocations are not investment advice.
