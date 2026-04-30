from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class InvestorStock(TypedDict):
    code: str
    name: str
    amount_millions: int | None
    ratio_percent: float


class InvestorDataset(TypedDict):
    name: str
    stocks: list[InvestorStock]


InvestorsDocument = dict[str, InvestorDataset]

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
INVESTOR_DATA_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"
EXPECTED_INVESTOR_NAMES: dict[str, str] = {
    "naito": "内藤征吾",
    "hikari": "光通信",
    "kiyohara": "清原達郎",
    "katayama": "片山晃",
    "imura": "井村俊哉",
    "gomi": "五味大輔",
    "one_warikabunihon": "one割安株日本株ファンド",
    "yoshida": "ヨシダトモヒロ",
}
EXPECTED_STOCK_COUNTS: dict[str, int] = {
    "naito": 113,
    "hikari": 451,
    "kiyohara": 18,
    "katayama": 27,
    "imura": 8,
    "gomi": 72,
    "one_warikabunihon": 10,
    "yoshida": 71,
}
EXPECTED_MAX_AMOUNTS: dict[str, int] = {
    "naito": 1150,
    "hikari": 66352,
    "kiyohara": 6681,
    "katayama": 7605,
    "imura": 3694,
    "gomi": 7422,
    "one_warikabunihon": 2066,
    "yoshida": 7246,
}
EXPECTED_PLACEHOLDER_CODES: dict[str, list[str]] = {
    "naito": ["3047", "1999"],
    "hikari": ["4842", "2759", "3734", "3731"],
    "yoshida": ["6076"],
}
EXPECTED_NULL_AMOUNT_CODES: dict[str, list[str]] = {
    "naito": ["3047", "1999", "5039"],
    "hikari": ["5039"],
    "yoshida": ["6076"],
}


def test_investor_data_contains_expected_datasets() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act
    investor_keys: set[str] = set(investors.keys())

    # Assert
    assert INVESTOR_DATA_PATH.exists()
    assert investor_keys == set(EXPECTED_INVESTOR_NAMES)
    for investor_key, expected_name in EXPECTED_INVESTOR_NAMES.items():
        assert investors[investor_key]["name"] == expected_name


def test_investor_data_uses_expected_schema() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act
    stock_lists: list[list[InvestorStock]] = [dataset["stocks"] for dataset in investors.values()]

    # Assert
    for stocks in stock_lists:
        for stock in stocks:
            assert isinstance(stock["code"], str)
            assert stock["code"] != ""
            assert isinstance(stock["name"], str)
            assert stock["name"] != ""
            amount: object = stock["amount_millions"]
            assert amount is None or _is_int(amount)
            assert _is_number(stock["ratio_percent"])


def test_investor_data_has_expected_counts_and_max_amounts() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act / Assert
    for investor_key, expected_count in EXPECTED_STOCK_COUNTS.items():
        stocks: list[InvestorStock] = investors[investor_key]["stocks"]
        amounts: list[int] = _non_null_amounts(stocks)

        assert len(stocks) == expected_count
        assert max(amounts) == EXPECTED_MAX_AMOUNTS[investor_key]


def test_investor_data_normalizes_missing_names_and_amounts() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act / Assert
    for investor_key, placeholder_codes in EXPECTED_PLACEHOLDER_CODES.items():
        stocks_by_code: dict[str, InvestorStock] = {
            stock["code"]: stock for stock in investors[investor_key]["stocks"]
        }
        for code in placeholder_codes:
            assert stocks_by_code[code]["name"] == f"（銘柄コード {code}）"

    for investor_key, null_amount_codes in EXPECTED_NULL_AMOUNT_CODES.items():
        stocks_by_code: dict[str, InvestorStock] = {
            stock["code"]: stock for stock in investors[investor_key]["stocks"]
        }
        for code in null_amount_codes:
            assert stocks_by_code[code]["amount_millions"] is None


def _load_investors_document() -> InvestorsDocument:
    raw_text: str = INVESTOR_DATA_PATH.read_text(encoding="utf-8")
    raw_document: object = cast(object, json.loads(raw_text))
    assert isinstance(raw_document, dict)

    normalized: InvestorsDocument = {}
    for investor_key, raw_dataset in raw_document.items():
        assert isinstance(investor_key, str)
        assert isinstance(raw_dataset, dict)

        raw_name: object = raw_dataset["name"]
        raw_stocks: object = raw_dataset["stocks"]

        assert isinstance(raw_name, str)
        assert isinstance(raw_stocks, list)

        stocks: list[InvestorStock] = []
        for raw_stock in raw_stocks:
            assert isinstance(raw_stock, dict)

            code: object = raw_stock["code"]
            name: object = raw_stock["name"]
            amount_millions: object = raw_stock["amount_millions"]
            ratio_percent: object = raw_stock["ratio_percent"]

            assert isinstance(code, str)
            assert isinstance(name, str)
            assert amount_millions is None or _is_int(amount_millions)
            assert _is_number(ratio_percent)

            stocks.append(
                {
                    "code": code,
                    "name": name,
                    "amount_millions": amount_millions,
                    "ratio_percent": float(ratio_percent),
                }
            )

        normalized[investor_key] = {
            "name": raw_name,
            "stocks": stocks,
        }

    return normalized


def _non_null_amounts(stocks: list[InvestorStock]) -> list[int]:
    amounts: list[int] = []
    for stock in stocks:
        amount: int | None = stock["amount_millions"]
        if amount is not None:
            amounts.append(amount)
    return amounts


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
