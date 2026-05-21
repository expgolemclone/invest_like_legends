"""Launch the portfolio/candidates web UI."""

from __future__ import annotations

import sys
from pathlib import Path

from investor_data import (
    build_investors_document,
    build_shareholder_candidates_document,
    build_stock_price_metadata,
    compute_metrics_map,
    load_major_shareholder_rows,
    load_stock_names,
    resolve_stocks_db_path,
    write_investors_document,
    write_shareholder_candidates_document,
    write_stock_price_metadata,
)
from stock_db.sources.price_refresh import (
    PriceRefreshCommandResult,
    PriceRefreshError,
    ensure_prices_fresh_for_api,
)
from stock_web_ui.handler import ApiHandler, json_route
from stock_web_ui.page import IndexPage
from stock_web_ui.serve import serve as _serve

_PROJECT_ROOT: Path = Path(__file__).resolve().parent
_DOCS_DIR: Path = _PROJECT_ROOT / "docs"
_STATIC_ROOT: Path = _DOCS_DIR / "assets"
_HANDBOOK_DATA_DIR: Path = _PROJECT_ROOT.parent / "japan_company_handbook" / "data"


def _load_and_enrich_investors() -> dict:
    """Build the investor payload from config, handbook DB, and stock metrics."""
    return build_investors_document()


def _load_shareholder_candidates() -> list[dict]:
    """Build candidates from the handbook DB."""
    return build_shareholder_candidates_document()


def _load_stock_price_metadata() -> dict[str, str | None]:
    """Build the latest stock price metadata from stocks.db."""
    return build_stock_price_metadata()


def _create_api_routes() -> dict[str, ApiHandler]:
    """Create API routes for the portfolio/candidates UI."""
    return {
        "/api/portfolio": json_route(lambda _params: _load_and_enrich_investors()),
        "/api/shareholder-candidates": json_route(lambda _params: _load_shareholder_candidates()),
        "/api/stock-price-meta": json_route(lambda _params: _load_stock_price_metadata()),
    }


def _ensure_prices_fresh() -> PriceRefreshCommandResult | None:
    """Refresh stock prices when the configured stocks DB is stale."""
    db_path = resolve_stocks_db_path()

    try:
        result = ensure_prices_fresh_for_api(db_path=db_path)
    except (PriceRefreshError, ValueError) as exc:
        print(f"Failed to update stock prices: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if result is None:
        return None

    update_message = (result.stderr or result.stdout).strip()
    suffix = f": {update_message}" if update_message else ""
    print(f"Updated stock prices{suffix}", file=sys.stderr)
    return result


def main() -> None:
    _ensure_prices_fresh()

    stock_names: dict[str, str] = load_stock_names()
    metrics_map: dict[str, dict[str, float | bool | None]] = compute_metrics_map()
    shareholder_rows = load_major_shareholder_rows()

    investors_doc = build_investors_document(
        stock_names=stock_names,
        metrics_map=metrics_map,
        shareholder_rows=shareholder_rows,
    )
    investors_output = write_investors_document(investors_doc)
    print(f"GitHub Pages JSON saved to {investors_output}")

    candidates_doc = build_shareholder_candidates_document(
        stock_names=stock_names,
        metrics_map=metrics_map,
        shareholder_rows=shareholder_rows,
    )
    candidates_output = write_shareholder_candidates_document(candidates_doc)
    print(f"GitHub Pages JSON saved to {candidates_output}")

    metadata_output = write_stock_price_metadata()
    print(f"GitHub Pages JSON saved to {metadata_output}")

    api_routes = _create_api_routes()
    _serve(
        static_root=_STATIC_ROOT,
        index_page=IndexPage(
            title="portfolio / candidates - invest_like_legends",
            loading_message="データを読み込み中です。",
            tab_aria_label="portfolio tabs",
        ),
        api_routes=api_routes,
        yazi_base_dir=_HANDBOOK_DATA_DIR,
    )


if __name__ == "__main__":
    main()
