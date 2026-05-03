"""保有銘柄の指標データを生成してJSONファイルに保存するスクリプト.

GitHub Actionsで毎日実行し、GitHub Pagesで表示するための静的データを作成する。
"""

from __future__ import annotations

import json
from pathlib import Path

from formula_screening.web import compute_all_stock_metrics

# 出力先
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "assets" / "data"
OUTPUT_FILE = OUTPUT_DIR / "metrics.json"


def main() -> None:
    """メイン処理."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("指標データを生成中...")
    metrics = compute_all_stock_metrics()
    print(f"  {len(metrics)} 銘柄の指標を計算しました")

    # JSONに保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"  {OUTPUT_FILE} に保存しました")


if __name__ == "__main__":
    main()
