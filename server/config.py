from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_DIR: Path = PROJECT_ROOT / "config"


class _ServerSection(TypedDict):
    host: str
    port: int


class _CliDefaultsToml(TypedDict):
    server: _ServerSection


class _BrowsersSection(TypedDict):
    shikiho: str
    monex: str


class _AllowedUrlPrefixesSection(TypedDict):
    shikiho: str
    monex: str


class _MagicNumbersToml(TypedDict):
    browsers: _BrowsersSection
    allowed_url_prefixes: _AllowedUrlPrefixesSection


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int

    def __repr__(self) -> str:
        return f"ServerConfig(host={self.host!r}, port={self.port})"


@dataclass(frozen=True, slots=True)
class BrowserEntry:
    command: str
    allowed_url_prefix: str

    def __repr__(self) -> str:
        return f"BrowserEntry(command={self.command!r}, prefix={self.allowed_url_prefix!r})"


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    entries: dict[str, BrowserEntry]

    def get_entry(self, key: str) -> BrowserEntry | None:
        return self.entries.get(key)

    def __repr__(self) -> str:
        return f"BrowserConfig(keys={list(self.entries.keys())})"


def load_server_config() -> ServerConfig:
    raw: _CliDefaultsToml = _load_toml("cli_defaults.toml")
    section: _ServerSection = raw["server"]
    return ServerConfig(host=section["host"], port=section["port"])


def load_browser_config() -> BrowserConfig:
    raw: _MagicNumbersToml = _load_toml("magic_numbers.toml")
    browsers: _BrowsersSection = raw["browsers"]
    prefixes: _AllowedUrlPrefixesSection = raw["allowed_url_prefixes"]
    entries: dict[str, BrowserEntry] = {
        key: BrowserEntry(command=cmd, allowed_url_prefix=prefixes[key])
        for key, cmd in browsers.items()
    }
    return BrowserConfig(entries=entries)


def _load_toml[T](filename: str) -> T:
    toml_path: Path = CONFIG_DIR / filename
    with toml_path.open("rb") as f:
        return tomllib.load(f)  # type: ignore[return-value]
