"""Launch the investor portfolio web UI."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from stock_web_ui.handler import ApiHandler
from stock_web_ui.serve import serve as _serve

_PROJECT_ROOT: Path = Path(__file__).resolve().parent
_DOCS_DIR: Path = _PROJECT_ROOT / "docs"
_STATIC_ROOT: Path = _DOCS_DIR / "assets"
_INDEX_PATH: Path = _DOCS_DIR / "index.html"
_INVESTORS_PATH: Path = _DOCS_DIR / "assets" / "data" / "investors.json"
_HANDBOOK_DATA_DIR: Path = _PROJECT_ROOT.parent / "japan_company_handbook" / "data"

_portfolio_payload: bytes | None = None


def _load_and_enrich_investors() -> bytes:
    """Read investors.json and enrich each stock with metrics from the DB."""
    with _INVESTORS_PATH.open("r", encoding="utf-8") as f:
        investors: dict = json.load(f)

    metrics_map: dict[str, dict] = _load_metrics()

    for _tab_key, dataset in investors.items():
        for stock in dataset.get("stocks", []):
            code: str = stock.get("code", "")
            m = metrics_map.get(code, {})
            stock["price"] = m.get("price")
            stock["net_cash_ratio"] = m.get("net_cash_ratio")
            stock["per"] = m.get("per")
            stock["equity_ratio"] = m.get("equity_ratio")
            stock["fcf_yield_avg"] = m.get("fcf_yield_avg")
            stock["croic"] = m.get("croic")

    return json.dumps(investors, ensure_ascii=False).encode("utf-8")


def _load_metrics() -> dict[str, dict]:
    """Load pre-computed metrics from metrics.json."""
    metrics_path: Path = _DOCS_DIR / "assets" / "data" / "metrics.json"
    if not metrics_path.is_file():
        return {}

    with metrics_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _create_api_routes() -> dict[str, ApiHandler]:
    """Create API routes for the investor portfolio UI."""
    global _portfolio_payload

    _portfolio_payload = _load_and_enrich_investors()

    def handle_portfolio(handler: BaseHTTPRequestHandler, _params: dict) -> None:
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(_portfolio_payload)))
        handler.end_headers()
        handler.wfile.write(_portfolio_payload)

    return {"/api/portfolio": handle_portfolio}


def main() -> None:
    api_routes = _create_api_routes()
    _serve(
        static_root=_STATIC_ROOT,
        index_path=_INDEX_PATH,
        api_routes=api_routes,
        yazi_base_dir=_HANDBOOK_DATA_DIR,
    )


if __name__ == "__main__":
    main()
