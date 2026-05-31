from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from investor_data import (
    build_stock_price_metadata,
    build_investors_document,
    build_shareholder_candidates_document,
    compute_metrics_map,
    load_investor_config,
    load_watch_codes,
    select_matching_shareholder_names,
    write_stock_price_metadata,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_PATH: Path = PROJECT_ROOT / "config" / "investors.json"
WATCH_CODES_PATH: Path = PROJECT_ROOT / "config" / "watch_codes.txt"
INVESTOR_DATA_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"
SHAREHOLDER_CANDIDATES_DATA_PATH: Path = (
    PROJECT_ROOT / "docs" / "assets" / "data" / "shareholder_candidates.json"
)
STOCK_PRICE_METADATA_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "stock-price-meta.json"
EXPECTED_INVESTOR_NAMES: dict[str, str] = {
    "watch": "監視銘柄",
    "hikari_all": "光通信_all",
    "hikari_core": "光通信",
    "hikari_kk_lps": "光通信KK",
    "uh_partners_2": "UH Partners 2",
    "uh_partners_3": "UH Partners 3",
    "sil": "エスアイエル",
    "noi": "エヌオーアイ",
    "ivy": "アイビー",
    "uh5": "UH5",
    "ft_communications": "FTコミュニケーションズ",
    "hikari_tsushin_inc": "Hikari Tsushin, Inc.",
    "hikari_1_dividend_lps": "光1号配当特化",
    "epark": "EPARK",
    "sakura_sonpo": "さくら損害保険",
    "uh7": "UH7",
    "uh4": "UH4",
    "hikari_tsushin_investments_okinawa": "HIKARI TSUSHIN INVESTMENTS OKINAWA",
    "broadpeak": "ブロードピーク",
    "freesia_macross": "フリージアマクロス",
    "naito": "内藤征吾",
    "kiyohara": "清原達郎",
    "katayama": "片山晃",
    "imura": "井村俊哉",
    "yoshida": "ヨシダトモヒロ",
    "nomura": "野村絢",
    "sasaki_beji": "佐々木ベジ",
}
EXPECTED_HIKARI_ALL_ALIASES: list[str] = [
    "株式会社光通信",
    "光通信株式会社",
    "光通信KK投資事業有限責任組合",
    "株式会社UH Partners 2",
    "UH Partners 2投資事業有限責任組合",
    "株式会社UH Partners 3",
    "UH Partners 3投資事業有限責任組合",
    "株式会社エスアイエル",
    "エスアイエル投資事業有限責任組合",
    "株式会社エヌオーアイ",
    "エヌオーアイ投資事業有限責任組合",
    "株式会社アイビー",
    "アイビー投資事業有限責任組合",
    "株式会社UH5",
    "株式会社EPARK",
    "株式会社さくら損害保険",
    "株式会社UH7",
    "株式会社UH4",
    "株式会社FTコミュニケーションズ",
    "Hikari Tsushin, Inc.",
    "HIKARI TSUSHIN INVESTMENTS OKINAWA",
    "光通信INVESTMENTS OKINAWA",
    "株式会社ブロードピーク",
    "光1号配当特化投資事業有限責任組合",
]
EXPECTED_WATCH_CODES: list[str] = [
    "1999",
    "4231",
    "5363",
    "8152",
    "5458",
    "3758",
    "6396",
    "8158",
    "1866",
    "8103",
    "9845",
    "9647",
    "7565",
    "6508",
    "7175",
    "9435",
]
METRIC_FIELDS: tuple[str, ...] = (
    "price",
    "price_date",
    "net_cash_ratio",
    "per_actual",
    "per",
    "per_next",
    "fcf_yield_avg",
    "total_payout_ratio",
    "equity_ratio",
    "peg_trailing_5",
    "peg_trailing_5_status",
    "peg_blended_5y_actual_2f",
    "peg_blended_5y_actual_2f_status",
    "dividend_yield",
    "has_preferred_shares",
    "croic",
    "fcf_cagr",
    "fcf_cagr_r2",
    "fcf_sma_cagr",
    "pbr",
)


def test_repo_config_contains_expected_investor_names_and_watch_codes() -> None:
    assert CONFIG_PATH.exists()
    assert WATCH_CODES_PATH.exists()

    investor_config = load_investor_config(CONFIG_PATH)

    assert {
        investor_key: entry["name"]
        for investor_key, entry in investor_config.items()
    } == EXPECTED_INVESTOR_NAMES
    assert investor_config["hikari_all"]["aliases"] == EXPECTED_HIKARI_ALL_ALIASES
    assert investor_config["naito"]["aliases"] == []
    assert load_watch_codes(WATCH_CODES_PATH) == EXPECTED_WATCH_CODES


def test_generated_investor_data_matches_config_and_schema() -> None:
    generated_document: dict[str, object] = json.loads(INVESTOR_DATA_PATH.read_text(encoding="utf-8"))
    assert isinstance(generated_document, dict)
    assert set(generated_document) == set(EXPECTED_INVESTOR_NAMES)

    for investor_key, investor_name in EXPECTED_INVESTOR_NAMES.items():
        raw_dataset: object = generated_document[investor_key]
        assert isinstance(raw_dataset, dict)
        assert raw_dataset["name"] == investor_name
        assert isinstance(raw_dataset["aliases"], list)
        assert all(isinstance(alias, str) and alias for alias in raw_dataset["aliases"])

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
                if metric_field == "has_preferred_shares":
                    assert metric_value is None or isinstance(metric_value, bool)
                elif metric_field == "price_date":
                    assert metric_value is None or isinstance(metric_value, str)
                elif metric_field.endswith("_status"):
                    assert metric_value is None or isinstance(metric_value, str)
                else:
                    assert metric_value is None or _is_number(metric_value)


def test_generated_shareholder_candidate_data_matches_schema() -> None:
    generated_document: object = json.loads(
        SHAREHOLDER_CANDIDATES_DATA_PATH.read_text(encoding="utf-8")
    )
    assert isinstance(generated_document, list)
    assert len(generated_document) <= 1000

    previous_rank: tuple[int, int, str] | None = None
    for raw_candidate in generated_document:
        assert isinstance(raw_candidate, dict)
        assert isinstance(raw_candidate["id"], str)
        assert raw_candidate["id"] != ""
        assert isinstance(raw_candidate["name"], str)
        assert raw_candidate["name"] != ""
        assert isinstance(raw_candidate["aliases"], list)
        assert all(isinstance(alias, str) and alias for alias in raw_candidate["aliases"])
        assert _is_int(raw_candidate["holding_count"])
        assert raw_candidate["holding_count"] >= 2
        assert _is_int(raw_candidate["priced_holding_count"])
        assert _is_int(raw_candidate["total_amount_millions"])

        ranking_key: tuple[int, int, str] = (
            -raw_candidate["total_amount_millions"],
            -raw_candidate["holding_count"],
            raw_candidate["name"],
        )
        if previous_rank is not None:
            assert previous_rank <= ranking_key
        previous_rank = ranking_key

        raw_stocks: object = raw_candidate["stocks"]
        assert isinstance(raw_stocks, list)
        assert len(raw_stocks) == raw_candidate["holding_count"]
        for raw_stock in raw_stocks:
            assert isinstance(raw_stock, dict)
            assert isinstance(raw_stock["code"], str)
            assert isinstance(raw_stock["name"], str)
            amount_millions: object = raw_stock["amount_millions"]
            assert amount_millions is None or _is_int(amount_millions)
            assert _is_number(raw_stock["ratio_percent"])
            for metric_field in METRIC_FIELDS:
                metric_value: object = raw_stock[metric_field]
                if metric_field == "has_preferred_shares":
                    assert metric_value is None or isinstance(metric_value, bool)
                elif metric_field == "price_date":
                    assert metric_value is None or isinstance(metric_value, str)
                elif metric_field.endswith("_status"):
                    assert metric_value is None or isinstance(metric_value, str)
                else:
                    assert metric_value is None or _is_number(metric_value)


def test_generated_stock_price_metadata_matches_schema() -> None:
    metadata: object = json.loads(STOCK_PRICE_METADATA_PATH.read_text(encoding="utf-8"))

    assert isinstance(metadata, dict)
    assert set(metadata) == {"price_date", "target_price_date"}
    price_date: object = metadata["price_date"]
    assert price_date is None or (
        isinstance(price_date, str)
        and len(price_date) == 10
        and price_date[4] == "-"
        and price_date[7] == "-"
    )
    target_price_date: object = metadata["target_price_date"]
    assert (
        isinstance(target_price_date, str)
        and len(target_price_date) == 10
        and target_price_date[4] == "-"
        and target_price_date[7] == "-"
    )


def test_stock_price_metadata_uses_stock_db_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_stock_price_metadata() -> dict[str, str]:
        return {"price_date": "2026-05-20", "target_price_date": "2026-05-20"}

    import stock_db.api as stock_db_api

    monkeypatch.setattr(stock_db_api, "get_stock_price_metadata", fake_get_stock_price_metadata)

    assert build_stock_price_metadata() == {
        "price_date": "2026-05-20",
        "target_price_date": "2026-05-20",
    }


def test_compute_metrics_map_uses_screening_payload_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_screening_strategy_payload(
        strategy_path: Path,
        *,
        return_all: bool,
    ) -> list[dict[str, object]]:
        captured["strategy_path"] = strategy_path
        captured["return_all"] = return_all
        return [
            {
                "code": "1301",
                "price": 1000.0,
                "price_date": "2026-05-20",
                "metrics": {
                    "net_cash_ratio": 1.1,
                    "per_actual": 5.0,
                    "per": 4.0,
                    "per_next": 3.0,
                    "equity_ratio": 60.0,
                    "dividend_yield": 2.5,
                    "total_payout_ratio": 12.3,
                    "pbr": 0.4,
                },
                "fcf_yield_avg": 0.12,
                "peg_trailing_5": 0.7,
                "peg_trailing_5_status": "ok",
                "peg_blended_5y_actual_2f": 0.6,
                "peg_blended_5y_actual_2f_status": "ok",
                "has_preferred_shares": False,
                "croic": 0.18,
                "fcf_cagr": 8.1,
                "fcf_cagr_r2": 0.77,
                "fcf_sma_cagr": 6.4,
            }
        ]

    import formula_screening.web as web_mod

    monkeypatch.setattr(
        web_mod,
        "run_screening_strategy_payload",
        fake_run_screening_strategy_payload,
    )

    assert compute_metrics_map()["1301"] == {
        "price": 1000.0,
        "price_date": "2026-05-20",
        "net_cash_ratio": 1.1,
        "per_actual": 5.0,
        "per": 4.0,
        "per_next": 3.0,
        "fcf_yield_avg": 0.12,
        "total_payout_ratio": 12.3,
        "equity_ratio": 60.0,
        "peg_trailing_5": 0.7,
        "peg_trailing_5_status": "ok",
        "peg_blended_5y_actual_2f": 0.6,
        "peg_blended_5y_actual_2f_status": "ok",
        "dividend_yield": 2.5,
        "has_preferred_shares": False,
        "croic": 0.18,
        "fcf_cagr": 8.1,
        "fcf_cagr_r2": 0.77,
        "fcf_sma_cagr": 6.4,
        "pbr": 0.4,
    }
    assert captured["return_all"] is True
    assert Path(captured["strategy_path"]).name == "net_cash_fcf.toml"


def test_write_stock_price_metadata_writes_json(tmp_path: Path) -> None:
    output_path = tmp_path / "stock-price-meta.json"

    result_path = write_stock_price_metadata(
        {"price_date": "2026-05-20", "target_price_date": "2026-05-20"},
        output_path=output_path,
    )

    assert result_path == output_path
    assert output_path.read_text(encoding="utf-8") == (
        '{\n  "price_date": "2026-05-20",\n'
        '  "target_price_date": "2026-05-20"\n}\n'
    )


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


def test_build_investors_document_uses_explicit_aliases_without_containment(
    tmp_path: Path,
) -> None:
    config_path: Path = tmp_path / "investors.json"
    config_path.write_text(
        json.dumps(
            {
                "hikari_all": {
                    "name": "光通信_all",
                    "aliases": [
                        "株式会社光通信",
                        "光通信KK投資事業有限責任組合",
                        "株式会社アイビー",
                        "アイビー投資事業有限責任組合",
                        "株式会社EPARK",
                        "株式会社さくら損害保険",
                        "株式会社UH7",
                        "株式会社UH4",
                        "株式会社FTコミュニケーションズ",
                        "Hikari Tsushin, Inc.",
                        "HIKARI TSUSHIN INVESTMENTS OKINAWA",
                        "光通信INVESTMENTS OKINAWA",
                        "株式会社ブロードピーク",
                    ],
                },
                "epark": {
                    "name": "EPARK",
                    "aliases": ["株式会社EPARK"],
                },
                "hikari_core": {
                    "name": "光通信",
                    "aliases": [
                        "株式会社光通信",
                        "光通信株式会社",
                    ],
                },
                "ivy": {
                    "name": "アイビー",
                    "aliases": [
                        "株式会社アイビー",
                        "アイビー投資事業有限責任組合",
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    watch_codes_path: Path = tmp_path / "watch_codes.txt"
    watch_codes_path.write_text("", encoding="utf-8")
    handbook_db_path: Path = tmp_path / "stock_performance.db"
    _create_handbook_db(
        handbook_db_path,
        rows=[
            ("1000", "光通信(株)", 10, 1.0),
            ("1001", "光通信KK投資事業有限責任組合", 20, 2.0),
            ("1002", "(株)アイビー", 30, 3.0),
            ("1003", "アイビー投資事業有限責任組合", 40, 4.0),
            ("1004", "アイビーピー(株)", 50, 5.0),
            ("1005", "(株)FTコミュニケーションズ", 60, 6.0),
            ("1006", "Hikari Tsushin, Inc.", 70, 7.0),
            ("1007", "光通信INVESTMENTS OKINAWA", 80, 8.0),
            ("1008", "(株)EPARK", 90, 9.0),
            ("1009", "(株)さくら損害保険", 100, 10.0),
            ("1010", "(株)UH7", 110, 11.0),
            ("1011", "(株)UH4", 120, 12.0),
            ("1012", "HIKARI TSUSHIN INVESTMENTS OKINAWA", 130, 13.0),
            ("1013", "(株)ブロードピーク", 140, 14.0),
        ],
    )

    document = build_investors_document(
        config_path=config_path,
        watch_codes_path=watch_codes_path,
        handbook_db_path=handbook_db_path,
        metrics_map={},
        stock_names={},
    )

    assert document["hikari_all"]["aliases"] == [
        "光通信(株)",
        "光通信KK投資事業有限責任組合",
        "(株)アイビー",
        "アイビー投資事業有限責任組合",
        "(株)FTコミュニケーションズ",
        "Hikari Tsushin, Inc.",
        "光通信INVESTMENTS OKINAWA",
        "(株)EPARK",
        "(株)さくら損害保険",
        "(株)UH7",
        "(株)UH4",
        "HIKARI TSUSHIN INVESTMENTS OKINAWA",
        "(株)ブロードピーク",
    ]
    assert [stock["code"] for stock in _stocks(document, "hikari_all")] == [
        "1000",
        "1001",
        "1002",
        "1003",
        "1005",
        "1006",
        "1007",
        "1008",
        "1009",
        "1010",
        "1011",
        "1012",
        "1013",
    ]
    assert document["epark"]["aliases"] == ["(株)EPARK"]
    assert [stock["code"] for stock in _stocks(document, "epark")] == ["1008"]
    assert document["hikari_core"]["aliases"] == ["光通信(株)"]
    assert [stock["code"] for stock in _stocks(document, "hikari_core")] == ["1000"]
    assert document["ivy"]["aliases"] == [
        "(株)アイビー",
        "アイビー投資事業有限責任組合",
    ]
    assert [stock["code"] for stock in _stocks(document, "ivy")] == ["1002", "1003"]


def test_build_investors_document_aggregates_shareholder_rows(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "investors.json"
    config_path.write_text(
        json.dumps(
            {
                "watch": "監視銘柄",
                "hikari": "光通信",
                "katayama": "片山晃",
                "naito": "内藤征吾",
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

    metrics_map: dict[str, dict[str, float | bool | str | None]] = {
        "1301": _metrics(
            price=800.0,
            per_actual=5.1,
            per=4.5,
            per_next=4.0,
            dividend_yield=3.75,
            peg_trailing_5=0.53,
            peg_trailing_5_status="ok",
            peg_blended_5y_actual_2f=0.41,
            peg_blended_5y_actual_2f_status="ok",
            has_preferred_shares=True,
            pbr=0.45,
        ),
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
    assert document["watch"]["aliases"] == []

    hikari_stocks: list[dict[str, object]] = _stocks(document, "hikari")
    assert document["hikari"]["aliases"] == [
        "光通信(株)",
        "光通信KK投資事業有限責任組合",
    ]
    assert [stock["code"] for stock in hikari_stocks] == ["1301", "1450"]
    assert hikari_stocks[0]["amount_millions"] == 80
    assert hikari_stocks[0]["ratio_percent"] == 0.5
    assert hikari_stocks[0]["per_actual"] == 5.1
    assert hikari_stocks[0]["per_next"] == 4.0
    assert hikari_stocks[0]["dividend_yield"] == 3.75
    assert hikari_stocks[0]["peg_trailing_5"] == 0.53
    assert hikari_stocks[0]["peg_trailing_5_status"] == "ok"
    assert hikari_stocks[0]["has_preferred_shares"] is True
    assert hikari_stocks[0]["pbr"] == 0.45
    assert hikari_stocks[1]["amount_millions"] == 750
    assert hikari_stocks[1]["ratio_percent"] == 5.1
    assert hikari_stocks[1]["net_cash_ratio"] == 1.2

    katayama_stocks: list[dict[str, object]] = _stocks(document, "katayama")
    assert document["katayama"]["aliases"] == ["片山善博"]
    assert katayama_stocks == [
        {
            "code": "1429",
            "name": "日本アクア",
            "amount_millions": 240,
            "ratio_percent": 0.6,
            "price": 1000.0,
            "price_date": None,
            "net_cash_ratio": None,
            "per_actual": None,
            "per": None,
            "per_next": None,
            "dividend_yield": None,
            "peg_trailing_5": None,
            "peg_trailing_5_status": None,
            "peg_blended_5y_actual_2f": None,
            "peg_blended_5y_actual_2f_status": None,
            "equity_ratio": 55.0,
            "fcf_yield_avg": None,
            "total_payout_ratio": None,
            "croic": None,
            "fcf_cagr": None,
            "fcf_cagr_r2": None,
            "fcf_sma_cagr": None,
            "has_preferred_shares": None,
            "pbr": None,
        }
    ]

    naito_stocks: list[dict[str, object]] = _stocks(document, "naito")
    assert document["naito"]["aliases"] == ["内藤征吾"]
    assert naito_stocks == [
        {
            "code": "1770",
            "name": "（銘柄コード 1770）",
            "amount_millions": None,
            "ratio_percent": 2.9,
            "price": None,
            "price_date": None,
            "net_cash_ratio": None,
            "per_actual": None,
            "per": None,
            "per_next": None,
            "dividend_yield": None,
            "peg_trailing_5": None,
            "peg_trailing_5_status": None,
            "peg_blended_5y_actual_2f": None,
            "peg_blended_5y_actual_2f_status": None,
            "equity_ratio": None,
            "fcf_yield_avg": None,
            "total_payout_ratio": None,
            "croic": None,
            "fcf_cagr": None,
            "fcf_cagr_r2": None,
            "fcf_sma_cagr": None,
            "has_preferred_shares": None,
            "pbr": None,
        }
    ]

    yoshida_stocks: list[dict[str, object]] = _stocks(document, "yoshida")
    assert document["yoshida"]["aliases"] == ["ヨシダ･トモヒロ"]
    assert yoshida_stocks[0]["amount_millions"] == 345
    assert yoshida_stocks[0]["croic"] == 0.19


def test_build_shareholder_candidates_document_groups_filters_and_ranks(tmp_path: Path) -> None:
    handbook_db_path: Path = tmp_path / "stock_performance.db"
    _create_handbook_db(
        handbook_db_path,
        rows=[
            ("1001", "(株)Alpha", 20, 1.1),
            ("1002", "Alpha㈱", 10, 0.5),
            ("1003", "Beta", 10, 0.8),
            ("1004", "Beta", 10, 0.7),
            ("1005", "自社従業員持株会", 50, 3.0),
            ("1006", "自社従業員持株会", 50, 3.0),
            ("1007", "Gamma証券", 10, 0.2),
            ("1008", "Gamma証券", 10, 0.2),
            ("1009", "Single Holder", 999, 9.9),
        ],
    )
    metrics_map: dict[str, dict[str, float | bool | str | None]] = {
        "1001": _metrics(price=1000.0),
        "1002": _metrics(price=2000.0),
        "1003": _metrics(price=5000.0),
        "1004": _metrics(price=None),
        "1005": _metrics(price=9000.0),
        "1006": _metrics(price=9000.0),
        "1007": _metrics(price=10000.0),
        "1008": _metrics(price=10000.0),
        "1009": _metrics(price=10000.0),
    }
    stock_names: dict[str, str] = {
        "1001": "Alpha 1",
        "1002": "Alpha 2",
        "1003": "Beta 1",
        "1004": "Beta 2",
    }

    candidates = build_shareholder_candidates_document(
        handbook_db_path=handbook_db_path,
        metrics_map=metrics_map,
        stock_names=stock_names,
        limit=10,
    )

    assert [candidate["name"] for candidate in candidates] == ["Beta", "Alpha㈱"]
    assert candidates[1] == {
        "id": "alpha",
        "name": "Alpha㈱",
        "aliases": ["(株)Alpha", "Alpha㈱"],
        "holding_count": 2,
        "priced_holding_count": 2,
        "total_amount_millions": 400,
        "stocks": [
            {
                "code": "1001",
                "name": "Alpha 1",
                "amount_millions": 200,
                "ratio_percent": 1.1,
                "price": 1000.0,
                "price_date": None,
                "net_cash_ratio": None,
                "per_actual": None,
                "per": None,
                "per_next": None,
                "dividend_yield": None,
                "peg_trailing_5": None,
                "peg_trailing_5_status": None,
                "peg_blended_5y_actual_2f": None,
                "peg_blended_5y_actual_2f_status": None,
                "equity_ratio": None,
                "fcf_yield_avg": None,
                "total_payout_ratio": None,
                "croic": None,
                "fcf_cagr": None,
                "fcf_cagr_r2": None,
                "fcf_sma_cagr": None,
                "has_preferred_shares": None,
                "pbr": None,
            },
            {
                "code": "1002",
                "name": "Alpha 2",
                "amount_millions": 200,
                "ratio_percent": 0.5,
                "price": 2000.0,
                "price_date": None,
                "net_cash_ratio": None,
                "per_actual": None,
                "per": None,
                "per_next": None,
                "dividend_yield": None,
                "peg_trailing_5": None,
                "peg_trailing_5_status": None,
                "peg_blended_5y_actual_2f": None,
                "peg_blended_5y_actual_2f_status": None,
                "equity_ratio": None,
                "fcf_yield_avg": None,
                "total_payout_ratio": None,
                "croic": None,
                "fcf_cagr": None,
                "fcf_cagr_r2": None,
                "fcf_sma_cagr": None,
                "has_preferred_shares": None,
                "pbr": None,
            },
        ],
    }
    assert candidates[0]["id"] == "beta"
    assert candidates[0]["holding_count"] == 2
    assert candidates[0]["priced_holding_count"] == 1
    assert candidates[0]["total_amount_millions"] == 500


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
    price_date: str | None = None,
    net_cash_ratio: float | None = None,
    per_actual: float | None = None,
    per: float | None = None,
    per_next: float | None = None,
    fcf_yield_avg: float | None = None,
    total_payout_ratio: float | None = None,
    equity_ratio: float | None = None,
    peg_trailing_5: float | None = None,
    peg_trailing_5_status: str | None = None,
    peg_blended_5y_actual_2f: float | None = None,
    peg_blended_5y_actual_2f_status: str | None = None,
    dividend_yield: float | None = None,
    has_preferred_shares: bool | None = None,
    croic: float | None = None,
    fcf_cagr: float | None = None,
    fcf_cagr_r2: float | None = None,
    fcf_sma_cagr: float | None = None,
    pbr: float | None = None,
) -> dict[str, float | bool | str | None]:
    return {
        "price": price,
        "price_date": price_date,
        "net_cash_ratio": net_cash_ratio,
        "per_actual": per_actual,
        "per": per,
        "per_next": per_next,
        "fcf_yield_avg": fcf_yield_avg,
        "total_payout_ratio": total_payout_ratio,
        "equity_ratio": equity_ratio,
        "peg_trailing_5": peg_trailing_5,
        "peg_trailing_5_status": peg_trailing_5_status,
        "peg_blended_5y_actual_2f": peg_blended_5y_actual_2f,
        "peg_blended_5y_actual_2f_status": peg_blended_5y_actual_2f_status,
        "dividend_yield": dividend_yield,
        "has_preferred_shares": has_preferred_shares,
        "croic": croic,
        "fcf_cagr": fcf_cagr,
        "fcf_cagr_r2": fcf_cagr_r2,
        "fcf_sma_cagr": fcf_sma_cagr,
        "pbr": pbr,
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
