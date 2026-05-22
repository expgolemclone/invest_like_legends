from __future__ import annotations

from pathlib import Path


def test_runtime_code_uses_stock_db_public_api() -> None:
    root = Path(__file__).resolve().parent.parent
    banned = (
        "STOCKS_DB_PATH",
        "stock_db.paths",
        "stock_db.storage",
        "stock_db.sources.price_refresh",
        "ensure_prices_fresh_for_api",
    )
    checked_files = [
        root / "investor_data.py",
        root / "serve.py",
        *sorted((root / "scripts").rglob("*.py")),
    ]

    violations: list[str] = []
    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                violations.append(f"{path.relative_to(root)}: {token}")

    assert violations == []
