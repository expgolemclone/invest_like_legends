from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from formula_screening.indicators.fcf import fcf_yield_avg
from formula_screening.metrics import compute_metrics
from stock_db.paths import STOCKS_DB_PATH
from stock_db.storage.connection import get_connection as _get_connection
from stock_db.storage.financials import get_financial_dict, get_historical_items
from stock_db.storage.prices import get_latest_price_with_shares

_FCF_YEARS: int = 10


@dataclass(frozen=True, slots=True)
class StockMetrics:
    ncr: float | None
    div: float | None
    fcf_y: float | None


def _get_conn() -> sqlite3.Connection:
    return _get_connection(STOCKS_DB_PATH)


def _compute_for_ticker(conn: sqlite3.Connection, ticker: str) -> StockMetrics | None:
    financials = get_financial_dict(conn, ticker)
    if not financials:
        return None

    price_data = get_latest_price_with_shares(conn, ticker)
    metrics = compute_metrics(financials, price_data["price"], price_data["shares_outstanding"])

    cf_history = get_historical_items(conn, ticker, "cf", n_periods=_FCF_YEARS)
    stock = {"metrics": metrics, "cf_history": cf_history}

    return StockMetrics(
        ncr=metrics.get("net_cash_ratio"),
        div=metrics.get("dividend_yield"),
        fcf_y=fcf_yield_avg(stock, years=_FCF_YEARS),
    )


def fetch_metrics(codes: list[str]) -> dict[str, dict[str, float | None]]:
    conn = _get_conn()
    try:
        result: dict[str, dict[str, float | None]] = {}
        for code in codes:
            m = _compute_for_ticker(conn, code)
            result[code] = {
                "ncr": m.ncr if m else None,
                "div": m.div if m else None,
                "fcf_y": m.fcf_y if m else None,
            }
        return result
    finally:
        conn.close()
