"""Enrich investors.json with metrics from formula_screening and write back.

Used by CI to generate the enriched data file for GitHub Pages deployment.
Uses the same public API as serve.py: formula_screening.web.compute_all_stock_metrics().
"""

from __future__ import annotations

import json
from pathlib import Path

from formula_screening.web import compute_all_stock_metrics

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
_INVESTORS_PATH: Path = _PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"


def main() -> None:
    print("investors.json を読み込み中...")
    with _INVESTORS_PATH.open("r", encoding="utf-8") as f:
        investors: dict = json.load(f)

    print("指標データを計算中...")
    metrics_map: dict[str, dict] = compute_all_stock_metrics()
    print(f"  {len(metrics_map)} 銘柄の指標を計算しました")

    for dataset in investors.values():
        for stock in dataset.get("stocks", []):
            code: str = stock.get("code", "")
            m = metrics_map.get(code, {})
            stock["price"] = m.get("price")
            stock["net_cash_ratio"] = m.get("net_cash_ratio")
            stock["per"] = m.get("per")
            stock["equity_ratio"] = m.get("equity_ratio")
            stock["fcf_yield_avg"] = m.get("fcf_yield_avg")
            stock["croic"] = m.get("croic")

    with _INVESTORS_PATH.open("w", encoding="utf-8") as f:
        json.dump(investors, f, ensure_ascii=False, indent=2)

    print(f"  {_INVESTORS_PATH} に保存しました")


if __name__ == "__main__":
    main()
