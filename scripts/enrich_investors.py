"""Generate public JSON data from handbook shareholder data and stock metrics."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from investor_data import (
    DEFAULT_SHAREHOLDER_CANDIDATE_DETAILS_OUTPUT_DIR,
    build_investors_document,
    build_shareholder_candidates_document,
    compute_metrics_map,
    load_major_shareholder_rows,
    load_stock_names,
    resolve_handbook_db_path,
    write_shareholder_candidate_detail_documents,
    write_investors_document,
    write_shareholder_candidates_document,
    write_stock_price_metadata,
)


def _auto_push_json(paths: list[Path], message: str) -> None:
    """Commit and push only the specified JSON files if they have changes."""
    import subprocess

    repo_root = PROJECT_ROOT
    rel_paths = [str(p.resolve().relative_to(repo_root)) for p in paths]
    diff = subprocess.run(
        ["jj", "diff", "--stat", "--"] + rel_paths,
        capture_output=True, text=True, cwd=str(repo_root),
    )
    if not diff.stdout.strip() or "0 files changed" in diff.stdout:
        return
    subprocess.run(
        ["jj", "commit", "-m", message, "--"] + rel_paths,
        check=True, cwd=str(repo_root),
    )
    subprocess.run(["jj", "git", "push"], check=True, cwd=str(repo_root))


def _sync_shikiho_dividends() -> None:
    from stock_db_bridge import sync_shikiho_dividends

    handbook_db_path = resolve_handbook_db_path()
    sync_shikiho_dividends(handbook_db_path)


def main() -> None:
    print("公開データを生成中...")
    _sync_shikiho_dividends()
    stock_names: dict[str, str] = load_stock_names()
    metrics_map: dict[str, dict[str, float | bool | str | None]] = compute_metrics_map()
    shareholder_rows = load_major_shareholder_rows()

    investors: dict = build_investors_document(
        stock_names=stock_names,
        metrics_map=metrics_map,
        shareholder_rows=shareholder_rows,
    )
    investors_output_path = write_investors_document(investors)
    print(f"  {investors_output_path} に保存しました")

    shareholder_candidates = build_shareholder_candidates_document(
        stock_names=stock_names,
        metrics_map=metrics_map,
        shareholder_rows=shareholder_rows,
    )
    candidates_output_path = write_shareholder_candidates_document(shareholder_candidates)
    print(f"  {candidates_output_path} に保存しました")
    candidate_detail_output_paths = write_shareholder_candidate_detail_documents(
        shareholder_candidates
    )
    print(
        f"  {DEFAULT_SHAREHOLDER_CANDIDATE_DETAILS_OUTPUT_DIR} に"
        f"{len(candidate_detail_output_paths)}件の詳細を保存しました"
    )

    metadata_output_path = write_stock_price_metadata()
    print(f"  {metadata_output_path} に保存しました")

    _auto_push_json(
        [
            investors_output_path,
            candidates_output_path,
            DEFAULT_SHAREHOLDER_CANDIDATE_DETAILS_OUTPUT_DIR,
            metadata_output_path,
        ],
        "Update investors data",
    )


if __name__ == "__main__":
    main()
