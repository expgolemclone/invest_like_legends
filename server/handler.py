from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from server.browser import OpenResult, open_in_browser
from server.config import BrowserConfig, PROJECT_ROOT


_STATIC_ROOT: Path = PROJECT_ROOT / "docs" / "assets"
_INDEX_PATH: Path = PROJECT_ROOT / "docs" / "index.html"

_MIME_OVERRIDES: dict[str, str] = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
}


class RequestHandler(BaseHTTPRequestHandler):
    browser_config: ClassVar[BrowserConfig]

    def do_GET(self) -> None:
        parsed_url: str = urlparse(self.path).path

        if parsed_url == "/open":
            self._handle_open()
        elif parsed_url == "/":
            self._serve_file(_INDEX_PATH, "text/html")
        elif parsed_url.startswith("/assets/"):
            filename: str = parsed_url[len("/assets/"):]
            file_path: Path = _STATIC_ROOT / filename
            if file_path.is_file() and _STATIC_ROOT in file_path.resolve().parents:
                content_type: str = _resolve_mime(file_path)
                self._serve_file(file_path, content_type)
            else:
                self._send_json_response(404, {"error": "Not found"})
        else:
            self._send_json_response(404, {"error": "Not found"})

    def _handle_open(self) -> None:
        query_params: dict[str, list[str]] = parse_qs(urlparse(self.path).query)
        browser_keys: list[str] = query_params.get("browser", [])
        urls: list[str] = query_params.get("url", [])

        if not browser_keys or not urls:
            self._send_json_response(400, {"error": "Missing browser or url parameter"})
            return

        result: OpenResult = open_in_browser(self.browser_config, browser_keys[0], urls[0])
        status_code: int = 200 if result.success else 400
        self._send_json_response(status_code, {"success": result.success, "message": result.message})

    def _serve_file(self, path: Path, content_type: str) -> None:
        content: bytes = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json_response(self, status_code: int, body: dict[str, str | bool]) -> None:
        payload: bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: str | int) -> None:
        print(f"[server] {args[0]} {args[1]}")


def _resolve_mime(path: Path) -> str:
    suffix: str = path.suffix.lower()
    if suffix in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[suffix]
    guessed: str | None = mimetypes.guess_type(str(path))[0]
    return guessed or "application/octet-stream"
