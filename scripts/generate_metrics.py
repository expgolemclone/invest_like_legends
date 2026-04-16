"""保有銘柄の指標データを生成してJSONファイルに保存するスクリプト.

GitHub Actionsで毎日実行し、GitHub Pagesで表示するための静的データを作成する。
"""

from __future__ import annotations

import json
from pathlib import Path

from formula_screening.config import MAGIC
from formula_screening.db.repository import (
    get_all_tickers,
    get_financial_dict,
    get_historical_items,
    get_latest_price_with_shares,
    get_stock_names,
)
from formula_screening.indicators import croic, fcf_yield_avg
from formula_screening.metrics import compute_metrics
from stock_db.paths import STOCKS_DB_PATH
from formula_screening.db.schema import get_connection

# 出力先
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "assets" / "data"
OUTPUT_FILE = OUTPUT_DIR / "metrics.json"


def generate_metrics() -> dict[str, dict[str, float | None]]:
    """全銘柄の指標を計算する.

    Returns:
        銘柄コードをキー、指標データを値とする辞書
    """
    conn = get_connection()
    try:
        names = get_stock_names(conn)
        all_codes = get_all_tickers(conn)

        result = {}

        for code in all_codes:
            if code not in names:
                continue

            try:
                financials = get_financial_dict(conn, code)
                price_data = get_latest_price_with_shares(conn, code)

                price = price_data["price"]
                shares = price_data["shares_outstanding"]

                metrics = compute_metrics(financials, price, shares)

                # 指標計算用のstock_dictを構築
                stock_dict = {
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

                # 過去のCFデータを取得
                cf_history = get_historical_items(
                    conn, code, "cf", n_periods=MAGIC["screening"]["fcf_years"]
                )
                stock_dict["cf_history"] = cf_history

                # fcf_yield_avg と croic を計算
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
            except (KeyError, ValueError, ZeroDivisionError, TypeError):
                # データ不足の銘柄は null 値を設定
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


def main() -> None:
    """メイン処理."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"指標データを生成中...")
    metrics = generate_metrics()
    print(f"  {len(metrics)} 銘柄の指標を計算しました")

    # JSONに保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"  {OUTPUT_FILE} に保存しました")


if __name__ == "__main__":
    main()
