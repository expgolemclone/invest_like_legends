"""Launch the portfolio/candidates web UI."""

from __future__ import annotations

import sys
from pathlib import Path

from investor_data import (
    ShareholderCandidateEntry,
    StockPriceMetadata,
    build_investors_document,
    build_shareholder_candidate_details_map,
    build_shareholder_candidates_document,
    build_stock_price_metadata,
    compute_metrics_map,
    load_major_shareholder_rows,
    load_stock_names,
    summarize_shareholder_candidates_document,
    write_shareholder_candidate_detail_documents,
    write_investors_document,
    write_shareholder_candidates_document,
    write_stock_price_metadata,
)
from stock_db_bridge import (
    PriceRefreshCommandResult,
    PriceRefreshError,
    ensure_prices_fresh,
)
from stock_web_ui.handler import ApiHandler, json_route
from stock_web_ui.page import IndexPage
from stock_web_ui.serve import serve as _serve

_PROJECT_ROOT: Path = Path(__file__).resolve().parent
_DOCS_DIR: Path = _PROJECT_ROOT / "docs"
_STATIC_ROOT: Path = _DOCS_DIR / "assets"
_HANDBOOK_DATA_DIR: Path = _PROJECT_ROOT.parent / "japan_company_handbook" / "data"


def _create_api_routes(
    *,
    investors_doc: dict,
    shareholder_candidates_doc: list[ShareholderCandidateEntry],
    stock_price_metadata: StockPriceMetadata,
) -> dict[str, ApiHandler]:
    """Create API routes for the portfolio/candidates UI."""
    candidate_summaries = summarize_shareholder_candidates_document(
        shareholder_candidates_doc
    )
    candidate_details = build_shareholder_candidate_details_map(
        shareholder_candidates_doc
    )

    return {
        "/api/portfolio": json_route(lambda _params: investors_doc),
        "/api/shareholder-candidates": json_route(lambda _params: candidate_summaries),
        "/api/shareholder-candidate": _create_candidate_detail_route(candidate_details),
        "/api/stock-price-meta": json_route(lambda _params: stock_price_metadata),
    }


def _create_candidate_detail_route(candidate_details: dict[str, dict]) -> ApiHandler:
    def route(handler, query_params):
        candidate_ids: list[str] = query_params.get("id", [])
        if not candidate_ids or not candidate_ids[0]:
            handler.send_json_response(400, {"error": "Missing id parameter"})
            return

        candidate_id: str = candidate_ids[0]
        detail: dict | None = candidate_details.get(candidate_id)
        if detail is None:
            handler.send_json_response(404, {"error": "Candidate not found"})
            return

        handler.send_json_response(200, detail)

    return route


def _ensure_prices_fresh() -> PriceRefreshCommandResult | None:
    """Refresh stock prices when stock_db reports stale data."""

    try:
        result = ensure_prices_fresh()
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
    metrics_map: dict[str, dict[str, float | bool | str | None]] = compute_metrics_map()
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
    candidate_detail_outputs = write_shareholder_candidate_detail_documents(candidates_doc)
    print(
        "GitHub Pages JSON saved to "
        f"{candidate_detail_outputs[0].parent} ({len(candidate_detail_outputs)} files)"
    )

    stock_price_metadata = build_stock_price_metadata()
    metadata_output = write_stock_price_metadata(stock_price_metadata)
    print(f"GitHub Pages JSON saved to {metadata_output}")

    api_routes = _create_api_routes(
        investors_doc=investors_doc,
        shareholder_candidates_doc=candidates_doc,
        stock_price_metadata=stock_price_metadata,
    )
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
