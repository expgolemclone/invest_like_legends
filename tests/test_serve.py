from __future__ import annotations

from pathlib import Path

import pytest

import serve
from stock_db.api import PriceRefreshCommandResult, PriceRefreshError


def test_ensure_prices_fresh_skips_command_when_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_ensure_prices_fresh() -> None:
        return None

    monkeypatch.setattr(serve, "ensure_prices_fresh", fake_ensure_prices_fresh)

    assert serve._ensure_prices_fresh() is None


def test_ensure_prices_fresh_runs_command_with_configured_db(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_ensure_prices_fresh() -> PriceRefreshCommandResult:
        return PriceRefreshCommandResult(stdout="", stderr="Refreshed stock prices: yahoo=1 ok")

    monkeypatch.setattr(serve, "ensure_prices_fresh", fake_ensure_prices_fresh)

    result = serve._ensure_prices_fresh()

    assert result is not None
    assert "Updated stock prices: Refreshed stock prices: yahoo=1 ok" in capsys.readouterr().err


def test_ensure_prices_fresh_exits_when_command_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_ensure_prices_fresh() -> PriceRefreshCommandResult:
        raise PriceRefreshError("Yahoo failed")

    monkeypatch.setattr(serve, "ensure_prices_fresh", fake_ensure_prices_fresh)

    with pytest.raises(SystemExit) as exc_info:
        serve._ensure_prices_fresh()

    assert exc_info.value.code == 1
    assert "Failed to update stock prices: Yahoo failed" in capsys.readouterr().err


def test_main_refreshes_prices_before_building_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []

    def fake_write_investors_document(doc: dict[str, object]) -> Path:
        assert doc == {"watch": {"stocks": []}}
        events.append("write_investors")
        return tmp_path / "investors.json"

    def fake_write_shareholder_candidates_document(doc: list[dict[str, object]]) -> Path:
        assert doc == [{"name": "candidate"}]
        events.append("write_candidates")
        return tmp_path / "shareholder_candidates.json"

    def fake_write_stock_price_metadata() -> Path:
        events.append("write_metadata")
        return tmp_path / "stock-price-meta.json"

    monkeypatch.setattr(serve, "_ensure_prices_fresh", lambda: events.append("refresh"))
    monkeypatch.setattr(serve, "load_stock_names", lambda: events.append("load_names") or {})
    monkeypatch.setattr(serve, "compute_metrics_map", lambda: events.append("load_metrics") or {})
    monkeypatch.setattr(serve, "load_major_shareholder_rows", lambda: events.append("load_rows") or [])
    monkeypatch.setattr(
        serve,
        "build_investors_document",
        lambda **kwargs: events.append("build_investors") or {"watch": {"stocks": []}},
    )
    monkeypatch.setattr(
        serve,
        "build_shareholder_candidates_document",
        lambda **kwargs: events.append("build_candidates") or [{"name": "candidate"}],
    )
    monkeypatch.setattr(serve, "write_investors_document", fake_write_investors_document)
    monkeypatch.setattr(
        serve,
        "write_shareholder_candidates_document",
        fake_write_shareholder_candidates_document,
    )
    monkeypatch.setattr(serve, "write_stock_price_metadata", fake_write_stock_price_metadata)
    monkeypatch.setattr(serve, "_serve", lambda **kwargs: events.append("serve"))

    serve.main()

    assert events == [
        "refresh",
        "load_names",
        "load_metrics",
        "load_rows",
        "build_investors",
        "write_investors",
        "build_candidates",
        "write_candidates",
        "write_metadata",
        "serve",
    ]


def test_create_api_routes_includes_portfolios_and_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(serve, "_load_and_enrich_investors", lambda: {"watch": {"stocks": []}})
    monkeypatch.setattr(serve, "_load_shareholder_candidates", lambda: [{"name": "candidate"}])
    monkeypatch.setattr(
        serve,
        "_load_stock_price_metadata",
        lambda: {"price_date": "2026-05-20", "target_price_date": "2026-05-20"},
    )

    assert set(serve._create_api_routes()) == {
        "/api/portfolio",
        "/api/shareholder-candidates",
        "/api/stock-price-meta",
    }
