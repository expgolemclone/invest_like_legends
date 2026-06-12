from __future__ import annotations

import json
from pathlib import Path

import pytest

import serve
from stock_db_bridge import PriceRefreshCommandResult, PriceRefreshError


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
    candidate_doc = [
        {
            "id": "candidate",
            "name": "candidate",
            "aliases": [],
            "holding_count": 0,
            "priced_holding_count": 0,
            "total_amount_millions": 0,
            "stocks": [],
        }
    ]

    def fake_write_investors_document(doc: dict[str, object]) -> Path:
        assert doc == {"watch": {"stocks": []}}
        events.append("write_investors")
        return tmp_path / "investors.json"

    def fake_write_shareholder_candidates_document(doc: list[dict[str, object]]) -> Path:
        assert doc == candidate_doc
        events.append("write_candidates")
        return tmp_path / "shareholder_candidates.json"

    def fake_write_shareholder_candidate_detail_documents(
        doc: list[dict[str, object]],
    ) -> list[Path]:
        assert doc == candidate_doc
        events.append("write_candidate_details")
        return [tmp_path / "shareholder_candidate_details" / "candidate.json"]

    def fake_write_stock_price_metadata(metadata: dict[str, str]) -> Path:
        assert metadata == {
            "price_date": "2026-05-20",
            "target_price_date": "2026-05-20",
        }
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
        lambda **kwargs: events.append("build_candidates") or candidate_doc,
    )
    monkeypatch.setattr(serve, "write_investors_document", fake_write_investors_document)
    monkeypatch.setattr(
        serve,
        "write_shareholder_candidates_document",
        fake_write_shareholder_candidates_document,
    )
    monkeypatch.setattr(
        serve,
        "write_shareholder_candidate_detail_documents",
        fake_write_shareholder_candidate_detail_documents,
    )
    monkeypatch.setattr(
        serve,
        "build_stock_price_metadata",
        lambda: events.append("build_metadata") or {
            "price_date": "2026-05-20",
            "target_price_date": "2026-05-20",
        },
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
        "write_candidate_details",
        "build_metadata",
        "write_metadata",
        "serve",
    ]


def test_create_api_routes_reuses_prebuilt_payloads() -> None:
    routes = serve._create_api_routes(
        investors_doc={"watch": {"stocks": []}},
        shareholder_candidates_doc=[
            {
                "id": "alpha",
                "name": "Alpha",
                "aliases": ["Alpha㈱"],
                "holding_count": 1,
                "priced_holding_count": 1,
                "total_amount_millions": 200,
                "stocks": [{"code": "1001"}],
            }
        ],
        stock_price_metadata={
            "price_date": "2026-05-20",
            "target_price_date": "2026-05-20",
        },
    )

    assert set(routes) == {
        "/api/portfolio",
        "/api/shareholder-candidates",
        "/api/shareholder-candidate",
        "/api/stock-price-meta",
    }

    handler = _JsonRecorder()
    routes["/api/portfolio"](handler, {})
    routes["/api/shareholder-candidates"](handler, {})
    routes["/api/stock-price-meta"](handler, {})

    assert handler.responses == [
        (200, {"watch": {"stocks": []}}),
        (
            200,
            [
                {
                    "id": "alpha",
                    "name": "Alpha",
                    "aliases": ["Alpha㈱"],
                    "holding_count": 1,
                    "priced_holding_count": 1,
                    "total_amount_millions": 200,
                }
            ],
        ),
        (
            200,
            {
                "price_date": "2026-05-20",
                "target_price_date": "2026-05-20",
            },
        ),
    ]


def test_candidate_detail_route_handles_found_missing_and_bad_request() -> None:
    routes = serve._create_api_routes(
        investors_doc={},
        shareholder_candidates_doc=[
            {
                "id": "alpha",
                "name": "Alpha",
                "aliases": ["Alpha㈱"],
                "holding_count": 1,
                "priced_holding_count": 1,
                "total_amount_millions": 200,
                "stocks": [{"code": "1001"}],
            }
        ],
        stock_price_metadata={},
    )

    handler = _JsonRecorder()
    route = routes["/api/shareholder-candidate"]

    route(handler, {"id": ["alpha"]})
    route(handler, {"id": ["missing"]})
    route(handler, {})

    assert handler.responses == [
        (
            200,
            {
                "id": "alpha",
                "name": "Alpha",
                "aliases": ["Alpha㈱"],
                "stocks": [{"code": "1001"}],
            },
        ),
        (404, {"error": "Candidate not found"}),
        (400, {"error": "Missing id parameter"}),
    ]


class _JsonRecorder:
    def __init__(self) -> None:
        self._status_code: int | None = None
        self.responses: list[tuple[int, object]] = []
        self.wfile = _JsonWriter(self)

    def send_response(self, status_code: int) -> None:
        self._status_code = status_code

    def send_header(self, _name: str, _value: str) -> None:
        return

    def end_headers(self) -> None:
        return

    def send_json_response(self, status_code: int, body: object) -> None:
        self.responses.append((status_code, body))


class _JsonWriter:
    def __init__(self, recorder: _JsonRecorder) -> None:
        self._recorder = recorder

    def write(self, payload: bytes) -> int:
        status_code = self._recorder._status_code
        assert status_code is not None
        self._recorder.responses.append(
            (status_code, json.loads(payload.decode("utf-8")))
        )
        return len(payload)
