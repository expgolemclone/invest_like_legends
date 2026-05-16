from __future__ import annotations

from pathlib import Path

import pytest

import serve
from stock_db.sources.stooq import StooqDailyPriceUpdateError, StooqPriceUpdateCommandResult


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_ensure_stooq_prices_fresh_skips_command_when_fresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "stocks.db"
    conn = FakeConnection()

    monkeypatch.setattr(serve, "resolve_stocks_db_path", lambda: db_path)
    monkeypatch.setattr(serve, "get_connection", lambda path: conn)
    monkeypatch.setattr(serve, "is_stooq_price_update_required", lambda db_conn: False)

    def unexpected_run_stooq_price_update_command(**kwargs: object) -> StooqPriceUpdateCommandResult:
        raise AssertionError(f"unexpected update: {kwargs}")

    monkeypatch.setattr(serve, "run_stooq_price_update_command", unexpected_run_stooq_price_update_command)

    assert serve._ensure_stooq_prices_fresh() is None
    assert conn.closed is True


def test_ensure_stooq_prices_fresh_runs_command_with_configured_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "stocks.db"
    conn = FakeConnection()
    captured: dict[str, object] = {}

    monkeypatch.setattr(serve, "resolve_stocks_db_path", lambda: db_path)
    monkeypatch.setattr(serve, "get_connection", lambda path: conn)
    monkeypatch.setattr(serve, "is_stooq_price_update_required", lambda db_conn: True)

    def fake_run_stooq_price_update_command(**kwargs: object) -> StooqPriceUpdateCommandResult:
        captured.update(kwargs)
        return StooqPriceUpdateCommandResult(stdout="", stderr="Imported 1 JP prices for 20260515")

    monkeypatch.setattr(serve, "run_stooq_price_update_command", fake_run_stooq_price_update_command)

    result = serve._ensure_stooq_prices_fresh()

    assert result is not None
    assert captured == {"db_path": db_path}
    assert conn.closed is True
    assert "Updated Stooq prices: Imported 1 JP prices for 20260515" in capsys.readouterr().err


def test_ensure_stooq_prices_fresh_exits_when_command_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "stocks.db"
    conn = FakeConnection()

    monkeypatch.setattr(serve, "resolve_stocks_db_path", lambda: db_path)
    monkeypatch.setattr(serve, "get_connection", lambda path: conn)
    monkeypatch.setattr(serve, "is_stooq_price_update_required", lambda db_conn: True)

    def fake_run_stooq_price_update_command(**kwargs: object) -> StooqPriceUpdateCommandResult:
        del kwargs
        raise StooqDailyPriceUpdateError("Unauthorized")

    monkeypatch.setattr(serve, "run_stooq_price_update_command", fake_run_stooq_price_update_command)

    with pytest.raises(SystemExit) as exc_info:
        serve._ensure_stooq_prices_fresh()

    assert exc_info.value.code == 1
    assert conn.closed is True
    assert "Failed to update Stooq prices: Unauthorized" in capsys.readouterr().err


def test_main_refreshes_prices_before_building_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []

    def fake_write_investors_document(doc: dict[str, object]) -> Path:
        assert doc == {"watch": {"stocks": []}}
        events.append("write")
        return tmp_path / "investors.json"

    monkeypatch.setattr(serve, "_ensure_stooq_prices_fresh", lambda: events.append("refresh"))
    monkeypatch.setattr(serve, "build_investors_document", lambda: events.append("build") or {"watch": {"stocks": []}})
    monkeypatch.setattr(serve, "write_investors_document", fake_write_investors_document)
    monkeypatch.setattr(serve, "_serve", lambda **kwargs: events.append("serve"))

    serve.main()

    assert events == ["refresh", "build", "write", "serve"]
