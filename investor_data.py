from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH: Path = PROJECT_ROOT / "config" / "investors.json"
DEFAULT_WATCH_CODES_PATH: Path = PROJECT_ROOT / "config" / "watch_codes.txt"
DEFAULT_OUTPUT_PATH: Path = PROJECT_ROOT / "docs" / "assets" / "data" / "investors.json"
DEFAULT_SHAREHOLDER_CANDIDATES_OUTPUT_PATH: Path = (
    PROJECT_ROOT / "docs" / "assets" / "data" / "shareholder_candidates.json"
)
DEFAULT_HANDBOOK_DB_PATH: Path = (
    PROJECT_ROOT.parent / "japan_company_handbook" / "data" / "stock_performance.db"
)
DEFAULT_SHAREHOLDER_CANDIDATE_LIMIT: int = 1000
DEFAULT_SHAREHOLDER_CANDIDATE_MIN_HOLDINGS: int = 2

_METRIC_FIELDS: tuple[str, ...] = (
    "price",
    "net_cash_ratio",
    "per_actual",
    "per",
    "per_next",
    "peg_trailing_5",
    "peg_blended_5y_actual_2f",
    "equity_ratio",
    "fcf_yield_avg",
    "croic",
    "has_preferred_shares",
)
_NORMALIZE_RE: re.Pattern[str] = re.compile(r"[\s\u3000・･·•\-ー_()（）\[\]【】.,/]")
_CORPORATE_TOKENS: tuple[str, ...] = (
    "株式会社",
    "(株)",
    "（株）",
    "㈱",
    "有限責任組合",
    "投資事業",
    "合同会社",
    "co.,ltd.",
    "co., ltd.",
    "coltd",
    "inc.",
    "inc",
)
_SHAREHOLDER_DISCOVERY_EXCLUDED_TOKENS: tuple[str, ...] = (
    "自己株",
    "持株会",
    "信託",
    "カストディ",
    "証券",
    "トラスト",
    "クライアント",
    "msip",
    "bny",
    "ssbt",
    "ssb",
    "jpmc",
    "ステートストリート",
    "モクスレイ",
    "jpモルガンチェースバンク",
    "バンクオブニューヨークメロン",
    "インタラクティブブローカーズ",
)


class ShareholderRow(TypedDict):
    stock_code: str
    shareholder_name: str
    shares: int | None
    ratio_pct: float | None


class StockEntry(TypedDict):
    code: str
    name: str
    amount_millions: int | None
    ratio_percent: float
    price: float | None
    net_cash_ratio: float | None
    per_actual: float | None
    per: float | None
    per_next: float | None
    peg_trailing_5: float | None
    peg_blended_5y_actual_2f: float | None
    equity_ratio: float | None
    fcf_yield_avg: float | None
    croic: float | None
    has_preferred_shares: bool | None


class InvestorEntry(TypedDict):
    name: str
    aliases: list[str]
    stocks: list[StockEntry]


class ShareholderCandidateEntry(TypedDict):
    id: str
    name: str
    aliases: list[str]
    holding_count: int
    priced_holding_count: int
    total_amount_millions: int
    stocks: list[StockEntry]


def load_investor_config(path: Path | None = None) -> dict[str, str]:
    config_path: Path = path or DEFAULT_CONFIG_PATH
    raw_document: object = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw_document, dict):
        raise ValueError(f"{config_path} must contain a JSON object")

    normalized: dict[str, str] = {}
    for key, value in raw_document.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"{config_path} must map strings to strings")
        normalized[key] = value

    return normalized


def load_watch_codes(path: Path | None = None) -> list[str]:
    watch_path: Path = path or DEFAULT_WATCH_CODES_PATH
    codes: list[str] = []
    for raw_line in watch_path.read_text(encoding="utf-8").splitlines():
        line: str = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        codes.append(line)
    return codes


def build_investors_document(
    *,
    config_path: Path | None = None,
    watch_codes_path: Path | None = None,
    handbook_db_path: Path | None = None,
    stocks_db_path: Path | None = None,
    metrics_map: dict[str, dict[str, float | bool | None]] | None = None,
    stock_names: dict[str, str] | None = None,
    shareholder_rows: list[ShareholderRow] | None = None,
) -> dict[str, InvestorEntry]:
    investor_config: dict[str, str] = load_investor_config(config_path)
    watch_codes: list[str] = load_watch_codes(watch_codes_path)
    names_map: dict[str, str] = (
        stock_names if stock_names is not None else load_stock_names(stocks_db_path)
    )
    resolved_metrics_map: dict[str, dict[str, float | bool | None]] = (
        metrics_map if metrics_map is not None else compute_metrics_map()
    )
    resolved_shareholder_rows: list[ShareholderRow] = (
        shareholder_rows if shareholder_rows is not None else load_major_shareholder_rows(handbook_db_path)
    )
    distinct_shareholder_names: list[str] = list(
        dict.fromkeys(row["shareholder_name"] for row in resolved_shareholder_rows)
    )

    document: dict[str, InvestorEntry] = {}
    for investor_key, investor_name in investor_config.items():
        aliases: list[str] = []
        if investor_key == "watch":
            stocks: list[StockEntry] = _build_watch_stocks(
                watch_codes=watch_codes,
                stock_names=names_map,
                metrics_map=resolved_metrics_map,
            )
        else:
            matched_names: list[str] = select_matching_shareholder_names(
                investor_name,
                distinct_shareholder_names,
            )
            aliases = matched_names
            stocks = _build_investor_stocks(
                matched_names=matched_names,
                shareholder_rows=resolved_shareholder_rows,
                stock_names=names_map,
                metrics_map=resolved_metrics_map,
            )

        document[investor_key] = {
            "name": investor_name,
            "aliases": aliases,
            "stocks": stocks,
        }

    return document


def build_shareholder_candidates_document(
    *,
    handbook_db_path: Path | None = None,
    stocks_db_path: Path | None = None,
    metrics_map: dict[str, dict[str, float | bool | None]] | None = None,
    stock_names: dict[str, str] | None = None,
    shareholder_rows: list[ShareholderRow] | None = None,
    limit: int = DEFAULT_SHAREHOLDER_CANDIDATE_LIMIT,
    min_holdings: int = DEFAULT_SHAREHOLDER_CANDIDATE_MIN_HOLDINGS,
) -> list[ShareholderCandidateEntry]:
    names_map: dict[str, str] = (
        stock_names if stock_names is not None else load_stock_names(stocks_db_path)
    )
    resolved_metrics_map: dict[str, dict[str, float | bool | None]] = (
        metrics_map if metrics_map is not None else compute_metrics_map()
    )
    resolved_shareholder_rows: list[ShareholderRow] = (
        shareholder_rows if shareholder_rows is not None else load_major_shareholder_rows(handbook_db_path)
    )

    rows_by_candidate_id: dict[str, list[ShareholderRow]] = defaultdict(list)
    alias_counts_by_candidate_id: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in resolved_shareholder_rows:
        shareholder_name: str = row["shareholder_name"]
        candidate_id: str = normalize_shareholder_name(shareholder_name)
        if not candidate_id or _is_discovery_excluded_shareholder_name(candidate_id):
            continue
        rows_by_candidate_id[candidate_id].append(row)
        alias_counts_by_candidate_id[candidate_id][shareholder_name] += 1

    candidates: list[ShareholderCandidateEntry] = []
    for candidate_id, rows in rows_by_candidate_id.items():
        stocks: list[StockEntry] = _build_stocks_from_shareholder_rows(
            rows=rows,
            stock_names=names_map,
            metrics_map=resolved_metrics_map,
        )
        if len(stocks) < min_holdings:
            continue

        alias_counts: dict[str, int] = alias_counts_by_candidate_id[candidate_id]
        aliases: list[str] = sorted(alias_counts)
        candidates.append(
            {
                "id": candidate_id,
                "name": _select_representative_shareholder_name(alias_counts),
                "aliases": aliases,
                "holding_count": len(stocks),
                "priced_holding_count": sum(
                    stock["amount_millions"] is not None for stock in stocks
                ),
                "total_amount_millions": sum(
                    stock["amount_millions"] or 0 for stock in stocks
                ),
                "stocks": stocks,
            }
        )

    candidates.sort(
        key=lambda candidate: (
            -candidate["total_amount_millions"],
            -candidate["holding_count"],
            candidate["name"],
        )
    )
    return candidates[:limit]


def write_investors_document(
    document: dict[str, InvestorEntry],
    *,
    output_path: Path | None = None,
) -> Path:
    resolved_output_path: Path = output_path or DEFAULT_OUTPUT_PATH
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved_output_path


def write_shareholder_candidates_document(
    document: list[ShareholderCandidateEntry],
    *,
    output_path: Path | None = None,
) -> Path:
    resolved_output_path: Path = output_path or DEFAULT_SHAREHOLDER_CANDIDATES_OUTPUT_PATH
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved_output_path


def load_major_shareholder_rows(db_path: Path | None = None) -> list[ShareholderRow]:
    resolved_db_path: Path = resolve_handbook_db_path(db_path)
    with sqlite3.connect(resolved_db_path) as con:
        rows = con.execute(
            """
            SELECT stock_code, shareholder_name, shares, ratio_pct
            FROM major_shareholders
            ORDER BY stock_code, rank
            """
        ).fetchall()

    normalized_rows: list[ShareholderRow] = []
    for stock_code, shareholder_name, shares, ratio_pct in rows:
        normalized_rows.append(
            {
                "stock_code": str(stock_code),
                "shareholder_name": str(shareholder_name),
                "shares": _normalize_int(shares),
                "ratio_pct": _normalize_float(ratio_pct),
            }
        )
    return normalized_rows


def load_stock_names(db_path: Path | None = None) -> dict[str, str]:
    resolved_db_path: Path = resolve_stocks_db_path(db_path)

    from stock_db.storage.connection import get_connection
    from stock_db.storage.stocks import get_stock_names

    with get_connection(resolved_db_path) as conn:
        return get_stock_names(conn)


def compute_metrics_map() -> dict[str, dict[str, float | bool | None]]:
    from formula_screening.web import compute_all_stock_metrics

    return compute_all_stock_metrics()


def resolve_handbook_db_path(path: Path | None = None) -> Path:
    if path is not None:
        return path

    env_path: str | None = os.environ.get("HANDBOOK_DB_PATH")
    if env_path:
        return Path(env_path)

    return DEFAULT_HANDBOOK_DB_PATH


def resolve_stocks_db_path(path: Path | None = None) -> Path:
    if path is not None:
        return path

    env_path: str | None = os.environ.get("STOCKS_DB_PATH")
    if env_path:
        return Path(env_path)

    from stock_db.paths import STOCKS_DB_PATH

    return STOCKS_DB_PATH


def select_matching_shareholder_names(
    investor_name: str,
    shareholder_names: list[str],
) -> list[str]:
    normalized_investor_name: str = normalize_shareholder_name(investor_name)
    if not normalized_investor_name:
        return []

    exact_matches: list[str] = [
        shareholder_name
        for shareholder_name in shareholder_names
        if normalize_shareholder_name(shareholder_name) == normalized_investor_name
    ]
    containment_matches: list[str] = [
        shareholder_name
        for shareholder_name in shareholder_names
        if _is_containment_match(normalized_investor_name, shareholder_name)
    ]
    if exact_matches:
        return exact_matches + [
            shareholder_name
            for shareholder_name in containment_matches
            if shareholder_name not in exact_matches
        ]

    if containment_matches:
        return containment_matches

    if _can_fallback_to_prefix_match(normalized_investor_name):
        prefix_matches: list[str] = [
            shareholder_name
            for shareholder_name in shareholder_names
            if normalize_shareholder_name(shareholder_name).startswith(
                normalized_investor_name[:2]
            )
        ]
        if prefix_matches:
            return prefix_matches

    return []


def normalize_shareholder_name(name: str) -> str:
    normalized: str = unicodedata.normalize("NFKC", name).lower()
    for token in _CORPORATE_TOKENS:
        normalized = normalized.replace(token, "")
    return _NORMALIZE_RE.sub("", normalized)


def _build_watch_stocks(
    *,
    watch_codes: list[str],
    stock_names: dict[str, str],
    metrics_map: dict[str, dict[str, float | bool | None]],
) -> list[StockEntry]:
    stocks: list[StockEntry] = []
    for code in watch_codes:
        stock: StockEntry = {
            "code": code,
            "name": _resolve_stock_name(code, stock_names),
            "amount_millions": None,
            "ratio_percent": 0,
        }
        _add_metrics(stock, metrics_map.get(code))
        stocks.append(stock)

    return sorted(stocks, key=lambda stock: str(stock["code"]))


def _build_investor_stocks(
    *,
    matched_names: list[str],
    shareholder_rows: list[ShareholderRow],
    stock_names: dict[str, str],
    metrics_map: dict[str, dict[str, float | bool | None]],
) -> list[StockEntry]:
    matched_name_set: set[str] = set(matched_names)
    matched_rows: list[ShareholderRow] = [
        row
        for row in shareholder_rows
        if row["shareholder_name"] in matched_name_set
    ]
    return _build_stocks_from_shareholder_rows(
        rows=matched_rows,
        stock_names=stock_names,
        metrics_map=metrics_map,
    )


def _build_stocks_from_shareholder_rows(
    *,
    rows: list[ShareholderRow],
    stock_names: dict[str, str],
    metrics_map: dict[str, dict[str, float | bool | None]],
) -> list[StockEntry]:
    rows_by_code: dict[str, list[ShareholderRow]] = defaultdict(list)
    for row in rows:
        rows_by_code[str(row["stock_code"])].append(row)

    stocks: list[StockEntry] = []
    for code, rows in rows_by_code.items():
        total_shares: int | None = _sum_nullable_ints(
            row["shares"] for row in rows
        )
        total_ratio: float = round(
            sum(row["ratio_pct"] or 0 for row in rows),
            2,
        )
        metrics: dict[str, float | bool | None] | None = metrics_map.get(code)

        stock: StockEntry = {
            "code": code,
            "name": _resolve_stock_name(code, stock_names),
            "amount_millions": _compute_amount_millions(total_shares, metrics),
            "ratio_percent": total_ratio,
        }
        _add_metrics(stock, metrics)
        stocks.append(stock)

    return sorted(stocks, key=lambda stock: str(stock["code"]))


def _add_metrics(
    stock: StockEntry,
    metrics: dict[str, float | bool | None] | None,
) -> None:
    metrics_dict: dict[str, float | bool | None] = metrics or {}
    for field in _METRIC_FIELDS:
        stock[field] = metrics_dict.get(field)


def _compute_amount_millions(
    shares: int | None,
    metrics: dict[str, float | bool | None] | None,
) -> int | None:
    if shares is None or metrics is None:
        return None

    price: float | None = metrics.get("price")
    if price is None:
        return None

    return int(round((shares * price) / 100))


def _resolve_stock_name(code: str, stock_names: dict[str, str]) -> str:
    stock_name: str | None = stock_names.get(code)
    if stock_name:
        return stock_name
    return f"（銘柄コード {code}）"


def _is_discovery_excluded_shareholder_name(normalized_name: str) -> bool:
    return any(
        normalize_shareholder_name(token) in normalized_name
        for token in _SHAREHOLDER_DISCOVERY_EXCLUDED_TOKENS
    )


def _select_representative_shareholder_name(alias_counts: dict[str, int]) -> str:
    return min(
        alias_counts,
        key=lambda alias: (
            -alias_counts[alias],
            len(alias),
            alias,
        ),
    )


def _is_containment_match(normalized_investor_name: str, shareholder_name: str) -> bool:
    normalized_shareholder_name: str = normalize_shareholder_name(shareholder_name)
    if not normalized_shareholder_name:
        return False

    shorter_name: str = min(
        normalized_investor_name,
        normalized_shareholder_name,
        key=len,
    )
    if not _allows_containment(shorter_name):
        return False

    return (
        normalized_investor_name in normalized_shareholder_name
        or normalized_shareholder_name in normalized_investor_name
    )


def _allows_containment(name: str) -> bool:
    if len(name) < 3:
        return False
    if name.isascii():
        return len(name) >= 5
    return True


def _can_fallback_to_prefix_match(name: str) -> bool:
    if len(name) < 2 or name.isascii():
        return False
    return all(_is_cjk_character(char) for char in name[:2])


def _is_cjk_character(char: str) -> bool:
    return unicodedata.east_asian_width(char) in {"W", "F"}


def _sum_nullable_ints(values: Iterable[int | None]) -> int | None:
    normalized_values: list[int] = [value for value in values if value is not None]
    if not normalized_values:
        return None
    return sum(normalized_values)


def _normalize_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _normalize_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
