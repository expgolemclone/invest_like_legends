"""Launch the investor portfolio web UI."""

from __future__ import annotations

from pathlib import Path

from investor_data import build_investors_document
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
