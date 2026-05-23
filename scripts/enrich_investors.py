"""Generate public JSON data from handbook shareholder data and stock metrics."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from investor_data import (
    build_investors_document,
    build_shareholder_candidates_document,
    compute_metrics_map,
    load_major_shareholder_rows,
    load_stock_names,
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


def main() -> None:
    print("公開データを生成中...")
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

    metadata_output_path = write_stock_price_metadata()
    print(f"  {metadata_output_path} に保存しました")

    _auto_push_json(
        [investors_output_path, candidates_output_path, metadata_output_path],
        "Update investors data",
    )


if __name__ == "__main__":
    main()
