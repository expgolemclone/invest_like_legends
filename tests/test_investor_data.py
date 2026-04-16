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


class InvestorsDocument(TypedDict):
    naito: InvestorDataset
    hikari: InvestorDataset


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
INVESTOR_DATA_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"


def test_investor_data_contains_expected_datasets() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act
    investor_keys: set[str] = set(investors.keys())

    # Assert
    assert INVESTOR_DATA_PATH.exists()
    assert investor_keys == {"naito", "hikari"}
    assert investors["naito"]["name"] == "内藤征吾"
    assert investors["hikari"]["name"] == "光通信"


def test_investor_data_uses_expected_schema() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()

    # Act
    stock_lists: list[list[InvestorStock]] = [investors["naito"]["stocks"], investors["hikari"]["stocks"]]

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

    # Act
    naito_stocks: list[InvestorStock] = investors["naito"]["stocks"]
    hikari_stocks: list[InvestorStock] = investors["hikari"]["stocks"]
    naito_amounts: list[int] = _non_null_amounts(naito_stocks)
    hikari_amounts: list[int] = _non_null_amounts(hikari_stocks)

    # Assert
    assert len(naito_stocks) == 113
    assert len(hikari_stocks) == 451
    assert max(naito_amounts) == 1150
    assert max(hikari_amounts) == 66352


def test_investor_data_normalizes_missing_names_and_amounts() -> None:
    # Arrange
    investors: InvestorsDocument = _load_investors_document()
    hikari_stocks: list[InvestorStock] = investors["hikari"]["stocks"]
    naito_stocks: list[InvestorStock] = investors["naito"]["stocks"]
    hikari_by_code: dict[str, InvestorStock] = {stock["code"]: stock for stock in hikari_stocks}
    naito_by_code: dict[str, InvestorStock] = {stock["code"]: stock for stock in naito_stocks}

    # Act
    hikari_placeholder_codes: list[str] = ["4842", "2759", "3734", "3731"]

    # Assert
    for code in hikari_placeholder_codes:
        assert hikari_by_code[code]["name"] == f"（銘柄コード {code}）"
    assert hikari_by_code["5039"]["amount_millions"] is None
    assert naito_by_code["5039"]["amount_millions"] is None


def _load_investors_document() -> InvestorsDocument:
    raw_text: str = INVESTOR_DATA_PATH.read_text(encoding="utf-8")
    raw_document: object = cast(object, json.loads(raw_text))
    assert isinstance(raw_document, dict)

    normalized: dict[str, InvestorDataset] = {}
    for investor_key in ("naito", "hikari"):
        raw_dataset: object = raw_document[investor_key]
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

    return {"naito": normalized["naito"], "hikari": normalized["hikari"]}


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
