"""Data access and preprocessing helpers."""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    """Convert raw Yahoo Finance history into price/return series."""
    if history.empty:
        return pd.DataFrame(columns=["price", "return"])

    frame = history[["Close"]].rename(columns={"Close": "price"}).copy()
    frame["return"] = frame["price"].pct_change()
    frame = frame.dropna()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    frame.index.name = "date"
    return frame


def fetch_price_history(
    tickers: list[str],
    start_date: str,
) -> dict[str, pd.DataFrame]:
    """Download historical prices for each ticker."""
    histories: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        try:
            history = yf.Ticker(ticker).history(start=start_date, auto_adjust=False)
        except Exception as exc:  # pragma: no cover - network/provider errors are not deterministic
            logger.warning("Failed to fetch %s: %s", ticker, exc)
            continue

        prepared = _prepare_history(history)
        if prepared.empty:
            logger.warning("No usable price history returned for %s", ticker)
            continue
        histories[ticker] = prepared

    return histories


def align_histories(histories: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Trim all series to their shared date intersection."""
    if not histories:
        return {}

    common_index = None
    for history in histories.values():
        index = pd.Index(history.index)
        common_index = index if common_index is None else common_index.intersection(index)

    if common_index is None or common_index.empty:
        return {}

    return {ticker: history.loc[common_index].copy() for ticker, history in histories.items()}
