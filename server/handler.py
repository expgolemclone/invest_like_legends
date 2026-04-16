from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from server.browser import OpenResult, open_in_browser
from server.config import BrowserConfig, PROJECT_ROOT

try:
    from formula_screening.db.repository import (
        get_all_tickers,
        get_financial_dict,
        get_historical_items,
        get_latest_price_with_shares,
        get_stock_names,
    )
    from formula_screening.config import MAGIC
    from formula_screening.metrics import compute_metrics
    from formula_screening.indicators import croic, fcf_yield_avg
    from stock_db.paths import STOCKS_DB_PATH
    from formula_screening.db.schema import get_connection
    _METRICS_AVAILABLE = True
except ImportError as e:
    _METRICS_AVAILABLE = False
    # Metrics module not available - /api/metrics will return 503
    print(f"[server] Metrics module not available: {e}")


_STATIC_ROOT: Path = PROJECT_ROOT / "docs" / "assets"
_INDEX_PATH: Path = PROJECT_ROOT / "docs" / "index.html"

_MIME_OVERRIDES: dict[str, str] = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
}


class RequestHandler(BaseHTTPRequestHandler):
    browser_config: ClassVar[BrowserConfig]

    def do_GET(self) -> None:
        parsed_url: str = urlparse(self.path).path

        if parsed_url == "/open":
            self._handle_open()
        elif parsed_url == "/api/metrics":
            self._handle_metrics()
        elif parsed_url == "/":
            self._serve_file(_INDEX_PATH, "text/html")
        elif parsed_url.startswith("/assets/"):
            filename: str = parsed_url[len("/assets/"):]
            file_path: Path = _STATIC_ROOT / filename
            if file_path.is_file() and _STATIC_ROOT in file_path.resolve().parents:
                content_type: str = _resolve_mime(file_path)
                self._serve_file(file_path, content_type)
            else:
                self._send_json_response(404, {"error": "Not found"})
        else:
            self._send_json_response(404, {"error": "Not found"})

    def _handle_metrics(self) -> None:
        """Handle /api/metrics endpoint."""
        if not _METRICS_AVAILABLE:
            self._send_json_response(503, {"error": "Metrics module not available"})
            return

        query_params: dict[str, list[str]] = parse_qs(urlparse(self.path).query)
        codes_param: list[str] = query_params.get("codes", [])

        if not codes_param:
            self._send_json_response(400, {"error": "Missing codes parameter"})
            return

        codes: list[str] = codes_param[0].split(",") if codes_param else []

        if not codes:
            self._send_json_response(400, {"error": "No codes provided"})
            return

        try:
            result: dict[str, dict[str, float | None]] = _compute_metrics_for_codes(codes)
            self._send_json_response(200, result)
        except LookupError as e:
            self._send_json_response(404, {"error": str(e)})
        except RuntimeError as e:
            self._send_json_response(500, {"error": str(e)})

    def _handle_open(self) -> None:
        query_params: dict[str, list[str]] = parse_qs(urlparse(self.path).query)
        browser_keys: list[str] = query_params.get("browser", [])
        urls: list[str] = query_params.get("url", [])

        if not browser_keys or not urls:
            self._send_json_response(400, {"error": "Missing browser or url parameter"})
            return

        result: OpenResult = open_in_browser(self.browser_config, browser_keys[0], urls[0])
        status_code: int = 200 if result.success else 400
        self._send_json_response(status_code, {"success": result.success, "message": result.message})

    def _serve_file(self, path: Path, content_type: str) -> None:
        content: bytes = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json_response(self, status_code: int, body: dict[str, str | bool]) -> None:
        payload: bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: str | int) -> None:
        print(f"[server] {args[0]} {args[1]}")


def _resolve_mime(path: Path) -> str:
    suffix: str = path.suffix.lower()
    if suffix in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[suffix]
    guessed: str | None = mimetypes.guess_type(str(path))[0]
    return guessed or "application/octet-stream"


def _compute_metrics_for_codes(codes: list[str]) -> dict[str, dict[str, float | None]]:
    """Compute metrics for given stock codes.

    Args:
        codes: List of stock codes (e.g., ["3385", "6627"])

    Returns:
        Dict mapping code to metrics dict.

    Raises:
        LookupError: If a stock code is not found in the database.
        RuntimeError: If metrics computation fails.
    """
    if not _METRICS_AVAILABLE:
        raise RuntimeError("Metrics module not available")

    conn = get_connection()
    try:
        names: dict[str, str] = get_stock_names(conn)
        result: dict[str, dict[str, float | None]] = {}

        for code in codes:
            if code not in names:
                continue

            try:
                financials = get_financial_dict(conn, code)
                price_data = get_latest_price_with_shares(conn, code)

                price = price_data["price"]
                shares = price_data["shares_outstanding"]

                metrics = compute_metrics(financials, price, shares)

                # Build stock dict for indicators
                stock_dict: dict = {
                    "ticker": code,
                    "name": names[code],
                    "price": price,
                    "shares_outstanding": shares,
                    "pl": financials.get("pl", {}),
                    "bs": financials.get("bs", {}),
                    "cf": financials.get("cf", {}),
                    "dividend": financials.get("dividend", {}),
                    "forecast": financials.get("forecast", {}),
                    "metrics": metrics,
                }

                # Get historical CF data for fcf_yield_avg
                cf_history = get_historical_items(
                    conn, code, "cf", n_periods=MAGIC["screening"]["fcf_years"]
                )
                stock_dict["cf_history"] = cf_history

                # Compute indicators
                fcf_yield = fcf_yield_avg(stock_dict)
                croic_value = croic(stock_dict)

                result[code] = {
                    "net_cash_ratio": metrics.get("net_cash_ratio"),
                    "per": metrics.get("per"),
                    "equity_ratio": metrics.get("equity_ratio"),
                    "fcf_yield_avg": fcf_yield,
                    "croic": croic_value,
                    "market_cap": metrics.get("market_cap"),
                }
            except (KeyError, ValueError, ZeroDivisionError, TypeError) as e:
                # Skip stocks with missing data or computation errors
                result[code] = {
                    "net_cash_ratio": None,
                    "per": None,
                    "equity_ratio": None,
                    "fcf_yield_avg": None,
                    "croic": None,
                    "market_cap": None,
                }

        return result
    finally:
        conn.close()
