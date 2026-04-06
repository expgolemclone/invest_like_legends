from __future__ import annotations

import subprocess
from dataclasses import dataclass

from server.config import BrowserConfig, BrowserEntry


@dataclass(frozen=True, slots=True)
class OpenResult:
    success: bool
    message: str

    def __repr__(self) -> str:
        return f"OpenResult(success={self.success}, message={self.message!r})"


def open_in_browser(browser_config: BrowserConfig, browser_key: str, url: str) -> OpenResult:
    entry: BrowserEntry | None = browser_config.get_entry(browser_key)
    if entry is None:
        return OpenResult(success=False, message=f"Unknown browser key: {browser_key}")

    if not url.startswith(entry.allowed_url_prefix):
        return OpenResult(
            success=False,
            message=f"URL not allowed for {browser_key}: {url}",
        )

    subprocess.Popen(
        [entry.command, url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return OpenResult(success=True, message=f"Opened in {entry.command}")
