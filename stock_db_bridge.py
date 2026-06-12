"""stock_db Rust CLI boundary used by invest_like_legends."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

JsonValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)

_PROJECT_ROOT = Path(__file__).resolve().parent
_DEFAULT_STOCK_DB_ROOT = _PROJECT_ROOT.parent / "stock_db"


@dataclass(frozen=True, slots=True)
class PriceRefreshCommandResult:
    stdout: str
    stderr: str


class PriceRefreshError(RuntimeError):
    """Raised when stock_db cannot refresh stale prices."""


def ensure_prices_fresh() -> PriceRefreshCommandResult | None:
    result = subprocess.run(
        ["uv", "run", "refresh-prices", "--if-needed", "--headless"],
        cwd=_stock_db_root(),
        env=_stock_db_env(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise PriceRefreshError(message or f"refresh-prices exited {result.returncode}")
    if not result.stdout and not result.stderr:
        return None
    return PriceRefreshCommandResult(stdout=result.stdout, stderr=result.stderr)


def get_stock_names() -> dict[str, str]:
    raw = _expect_dict(_run_stock_db_json(["downstream-stock-names"]))
    return {str(code): str(name) for code, name in raw.items()}


def get_stock_price_metadata() -> dict[str, str | None]:
    ensure_prices_fresh()
    raw = _expect_dict(_run_stock_db_json(["downstream-stock-price-metadata"]))
    return {
        "price_date": _optional_str(raw.get("price_date")),
        "target_price_date": str(raw["target_price_date"]),
    }


def sync_shikiho_dividends(shikiho_db_path: Path) -> None:
    result = subprocess.run(
        [
            "cargo",
            "run",
            "-q",
            "-p",
            "edinet-xbrl",
            "--",
            "sync-shikiho-dividends",
            "--shikiho-db",
            str(shikiho_db_path),
        ],
        cwd=_stock_db_root(),
        env=_stock_db_env(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(message or f"sync-shikiho-dividends exited {result.returncode}")


def _stock_db_root() -> Path:
    configured = os.environ.get("STOCK_DB_ROOT")
    root = Path(configured).expanduser() if configured else _DEFAULT_STOCK_DB_ROOT
    if not root.is_dir():
        raise ValueError(f"stock_db root does not exist: {root}")
    return root


def _stock_db_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("STOCK_DB_ROOT", str(_stock_db_root()))
    return env


def _run_stock_db_json(args: list[str]) -> JsonValue:
    result = subprocess.run(
        ["cargo", "run", "-q", "-p", "edinet-xbrl", "--", *args],
        cwd=_stock_db_root(),
        env=_stock_db_env(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise ValueError(message or f"edinet-xbrl {' '.join(args)} exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"edinet-xbrl {' '.join(args)} emitted invalid JSON") from exc


def _expect_dict(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object, got {type(value).__name__}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
