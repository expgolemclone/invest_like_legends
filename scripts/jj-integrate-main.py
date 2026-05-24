"""Integrate the current jj change into main and push main."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)


def main() -> None:
    message: str | None = sys.argv[1] if len(sys.argv) > 1 else None
    if len(sys.argv) > 2:
        raise SystemExit("usage: python3 scripts/jj-integrate-main.py [message]")
    if message:
        _run(["jj", "describe", "-m", message])
    _run(["jj", "rebase", "-d", "main"])
    _run(["jj", "bookmark", "set", "main", "-r", "@"])
    _run(["jj", "git", "push", "--bookmark", "main"])


if __name__ == "__main__":
    main()
