"""Launch the investor portfolio web UI."""

from __future__ import annotations

import json
from pathlib import Path

from formula_screening.web import compute_all_stock_metrics
from stock_web_ui.handler import ApiHandler, json_route
from stock_web_ui.page import IndexPage
from stock_web_ui.serve import serve as _serve

_PROJECT_ROOT: Path = Path(__file__).resolve().parent
_DOCS_DIR: Path = _PROJECT_ROOT / "docs"
_STATIC_ROOT: Path = _DOCS_DIR / "assets"
_INVESTORS_PATH: Path = _DOCS_DIR / "assets" / "data" / "investors.json"
_HANDBOOK_DATA_DIR: Path = _PROJECT_ROOT.parent / "japan_company_handbook" / "data"


def _load_and_enrich_investors() -> dict:
    """Read investors.json and enrich each stock with metrics from the DB."""
    with _INVESTORS_PATH.open("r", encoding="utf-8") as f:
        investors: dict = json.load(f)

    metrics_map: dict[str, dict] = _compute_metrics_map()

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

    return investors


def _compute_metrics_map() -> dict[str, dict[str, float | None]]:
    """Compute metrics for all tickers via the formula_screening public API."""
    return compute_all_stock_metrics()


def _create_api_routes() -> dict[str, ApiHandler]:
    """Create API routes for the investor portfolio UI."""
    return {"/api/portfolio": json_route(lambda _params: _load_and_enrich_investors())}


def main() -> None:
    api_routes = _create_api_routes()
    _serve(
        static_root=_STATIC_ROOT,
        index_page=IndexPage(
            title="保有銘柄ビューア - 四季報オンラインリンク一覧",
            loading_message="投資家データを読み込み中です。",
            tab_aria_label="投資家切替",
        ),
        api_routes=api_routes,
        yazi_base_dir=_HANDBOOK_DATA_DIR,
    )


if __name__ == "__main__":
    main()
