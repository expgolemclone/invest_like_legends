from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from investor_data import (
    build_investors_document,
    load_investor_config,
    load_watch_codes,
    select_matching_shareholder_names,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_PATH: Path = PROJECT_ROOT / "config" / "investors.json"
WATCH_CODES_PATH: Path = PROJECT_ROOT / "config" / "watch_codes.txt"
INVESTOR_DATA_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"
EXPECTED_INVESTOR_NAMES: dict[str, str] = {
    "watch": "監視銘柄",
    "naito": "内藤征吾",
    "hikari": "光通信",
    "kiyohara": "清原達郎",
    "katayama": "片山晃",
    "imura": "井村俊哉",
    "gomi": "五味大輔",
    "one_warikabunihon": "one割安株日本株ファンド",
    "yoshida": "ヨシダトモヒロ",
}
EXPECTED_WATCH_CODES: list[str] = [
    "3020",
    "2991",
    "2986",
    "2982",
    "8152",
    "5280",
    "1828",
    "1832",
    "1847",
    "1892",
    "211A",
    "2286",
    "3962",
    "4040",
    "3047",
    "3280",
    "3299",
    "3300",
    "3441",
    "3442",
    "3452",
    "3477",
    "3482",
    "3486",
    "3489",
    "3551",
    "3583",
    "3640",
    "3670",
    "3675",
    "367A",
    "4092",
    "4116",
    "4119",
    "414A",
    "421A",
    "4231",
    "4234",
    "4246",
    "4386",
    "4393",
    "4421",
    "4440",
    "4476",
    "4685",
    "4691",
    "4750",
    "4752",
    "476A",
    "477A",
    "479A",
    "480A",
    "483A",
    "4848",
    "4977",
    "4992",
    "5010",
    "5013",
    "5204",
    "5284",
    "5285",
    "5288",
    "5445",
    "5607",
    "5989",
]
METRIC_FIELDS: tuple[str, ...] = (
    "price",
    "net_cash_ratio",
    "per_actual",
    "per",
    "per_next",
    "peg_5",
    "equity_ratio",
    "fcf_yield_avg",
    "croic",
)


def test_repo_config_contains_expected_investor_names_and_watch_codes() -> None:
    assert CONFIG_PATH.exists()
    assert WATCH_CODES_PATH.exists()
    assert load_investor_config(CONFIG_PATH) == EXPECTED_INVESTOR_NAMES
    assert load_watch_codes(WATCH_CODES_PATH) == EXPECTED_WATCH_CODES


def test_generated_investor_data_matches_config_and_schema() -> None:
    generated_document: dict[str, object] = json.loads(INVESTOR_DATA_PATH.read_text(encoding="utf-8"))
    assert isinstance(generated_document, dict)
    assert set(generated_document) == set(EXPECTED_INVESTOR_NAMES)

    for investor_key, investor_name in EXPECTED_INVESTOR_NAMES.items():
        raw_dataset: object = generated_document[investor_key]
        assert isinstance(raw_dataset, dict)
        assert raw_dataset["name"] == investor_name

        raw_stocks: object = raw_dataset["stocks"]
        assert isinstance(raw_stocks, list)
        for raw_stock in raw_stocks:
            assert isinstance(raw_stock, dict)
            assert isinstance(raw_stock["code"], str)
            assert raw_stock["code"] != ""
            assert isinstance(raw_stock["name"], str)
            assert raw_stock["name"] != ""
            amount_millions: object = raw_stock["amount_millions"]
            assert amount_millions is None or _is_int(amount_millions)
            assert _is_number(raw_stock["ratio_percent"])
            for metric_field in METRIC_FIELDS:
                metric_value: object = raw_stock[metric_field]
                assert metric_value is None or _is_number(metric_value)


def test_shareholder_name_matching_handles_aliases_and_prefix_fallback() -> None:
    shareholder_names: list[str] = [
        "光通信(株)",
        "光通信KK投資事業有限責任組合",
        "ヨシダ･トモヒロ",
        "片山善博",
        "(株)Bright Stone",
    ]

    assert select_matching_shareholder_names("光通信", shareholder_names) == [
        "光通信(株)",
        "光通信KK投資事業有限責任組合",
    ]
    assert select_matching_shareholder_names("ヨシダトモヒロ", shareholder_names) == [
        "ヨシダ･トモヒロ",
    ]
    assert select_matching_shareholder_names("片山晃", shareholder_names) == [
        "片山善博",
    ]
    assert select_matching_shareholder_names("one割安株日本株ファンド", shareholder_names) == []


def test_build_investors_document_aggregates_shareholder_rows(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "investors.json"
    config_path.write_text(
        json.dumps(
            {
                "watch": "監視銘柄",
                "hikari": "光通信",
                "katayama": "片山晃",
                "naito": "内藤征吾",
                "one_warikabunihon": "one割安株日本株ファンド",
                "yoshida": "ヨシダトモヒロ",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    watch_codes_path: Path = tmp_path / "watch_codes.txt"
    watch_codes_path.write_text("2991\n", encoding="utf-8")

    handbook_db_path: Path = tmp_path / "stock_performance.db"
    _create_handbook_db(
        handbook_db_path,
        rows=[
            ("1450", "光通信(株)", 50, 4.0),
            ("1450", "光通信KK投資事業有限責任組合", 25, 1.1),
            ("1301", "光通信(株)", 10, 0.5),
            ("1429", "片山善博", 24, 0.6),
            ("1770", "内藤征吾", 30, 2.9),
            ("1518", "ヨシダ･トモヒロ", 23, 1.8),
        ],
    )

    metrics_map: dict[str, dict[str, float | None]] = {
        "1301": _metrics(price=800.0, per_actual=5.1, per=4.5, per_next=4.0, peg_5=0.53),
        "1429": _metrics(price=1000.0, equity_ratio=55.0),
        "1450": _metrics(price=1000.0, net_cash_ratio=1.2),
        "1518": _metrics(price=1500.0, croic=0.19),
        "2991": _metrics(price=500.0),
        "1770": _metrics(price=None),
    }
    stock_names: dict[str, str] = {
        "1301": "極洋サンプル",
        "1429": "日本アクア",
        "1450": "田中建設工業",
        "1518": "三井松島HD",
        "2991": "ランドネット",
    }

    document: dict[str, dict[str, object]] = build_investors_document(
        config_path=config_path,
        watch_codes_path=watch_codes_path,
        handbook_db_path=handbook_db_path,
        metrics_map=metrics_map,
        stock_names=stock_names,
    )

    watch_stocks: list[dict[str, object]] = _stocks(document, "watch")
    assert [stock["code"] for stock in watch_stocks] == ["2991"]
    assert watch_stocks[0]["name"] == "ランドネット"
    assert watch_stocks[0]["amount_millions"] is None
    assert watch_stocks[0]["ratio_percent"] == 0
    assert watch_stocks[0]["price"] == 500.0
    assert watch_stocks[0]["per_actual"] is None

    hikari_stocks: list[dict[str, object]] = _stocks(document, "hikari")
    assert [stock["code"] for stock in hikari_stocks] == ["1301", "1450"]
    assert hikari_stocks[0]["amount_millions"] == 80
    assert hikari_stocks[0]["ratio_percent"] == 0.5
    assert hikari_stocks[0]["per_actual"] == 5.1
    assert hikari_stocks[0]["per_next"] == 4.0
    assert hikari_stocks[0]["peg_5"] == 0.53
    assert hikari_stocks[1]["amount_millions"] == 750
    assert hikari_stocks[1]["ratio_percent"] == 5.1
    assert hikari_stocks[1]["net_cash_ratio"] == 1.2

    katayama_stocks: list[dict[str, object]] = _stocks(document, "katayama")
    assert katayama_stocks == [
        {
            "code": "1429",
            "name": "日本アクア",
            "amount_millions": 240,
            "ratio_percent": 0.6,
            "price": 1000.0,
            "net_cash_ratio": None,
            "per_actual": None,
            "per": None,
            "per_next": None,
            "peg_5": None,
            "equity_ratio": 55.0,
            "fcf_yield_avg": None,
            "croic": None,
        }
    ]

    naito_stocks: list[dict[str, object]] = _stocks(document, "naito")
    assert naito_stocks == [
        {
            "code": "1770",
            "name": "（銘柄コード 1770）",
            "amount_millions": None,
            "ratio_percent": 2.9,
            "price": None,
            "net_cash_ratio": None,
            "per_actual": None,
            "per": None,
            "per_next": None,
            "peg_5": None,
            "equity_ratio": None,
            "fcf_yield_avg": None,
            "croic": None,
        }
    ]

    yoshida_stocks: list[dict[str, object]] = _stocks(document, "yoshida")
    assert yoshida_stocks[0]["amount_millions"] == 345
    assert yoshida_stocks[0]["croic"] == 0.19

    assert _stocks(document, "one_warikabunihon") == []


def _create_handbook_db(
    db_path: Path,
    *,
    rows: list[tuple[str, str, int | None, float | None]],
) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE major_shareholders (
                stock_code TEXT NOT NULL,
                rank INTEGER NOT NULL DEFAULT 1,
                shareholder_name TEXT NOT NULL,
                shares INTEGER,
                ratio_pct REAL
            )
            """
        )
        con.executemany(
            """
            INSERT INTO major_shareholders (stock_code, rank, shareholder_name, shares, ratio_pct)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (stock_code, rank, shareholder_name, shares, ratio_pct)
                for rank, (stock_code, shareholder_name, shares, ratio_pct) in enumerate(rows, start=1)
            ],
        )
        con.commit()


def _metrics(
    *,
    price: float | None,
    net_cash_ratio: float | None = None,
    per_actual: float | None = None,
    per: float | None = None,
    per_next: float | None = None,
    peg_5: float | None = None,
    equity_ratio: float | None = None,
    fcf_yield_avg: float | None = None,
    croic: float | None = None,
) -> dict[str, float | None]:
    return {
        "price": price,
        "net_cash_ratio": net_cash_ratio,
        "per_actual": per_actual,
        "per": per,
        "per_next": per_next,
        "peg_5": peg_5,
        "equity_ratio": equity_ratio,
        "fcf_yield_avg": fcf_yield_avg,
        "croic": croic,
    }


def _stocks(
    document: dict[str, dict[str, object]],
    investor_key: str,
) -> list[dict[str, object]]:
    raw_stocks: object = document[investor_key]["stocks"]
    assert isinstance(raw_stocks, list)
    for stock in raw_stocks:
        assert isinstance(stock, dict)
    return raw_stocks


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
