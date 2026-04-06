from __future__ import annotations

import os
import signal
import subprocess
import time
from http.server import HTTPServer
from pathlib import Path

from server.config import ServerConfig, load_browser_config, load_server_config
from server.handler import RequestHandler


_LISTEN_STATE: str = "0A"
_PROC_PATH: Path = Path("/proc")
_TERM_TIMEOUT_SECONDS: float = 1.0
_POLL_INTERVAL_SECONDS: float = 0.1
_STARTUP_BROWSER_COMMAND: str = "qutebrowser"
_STARTUP_BROWSER_TARGET: str = "window"


def main() -> None:
    server_config: ServerConfig = load_server_config()
    RequestHandler.browser_config = load_browser_config()

    _release_port_if_needed(server_config.host, server_config.port)
    address: tuple[str, int] = (server_config.host, server_config.port)
    httpd: HTTPServer = HTTPServer(address, RequestHandler)
    server_url: str = f"http://{server_config.host}:{server_config.port}"
    print(f"Serving on {server_url}")
    _open_startup_browser(server_url)
    httpd.serve_forever()


def _release_port_if_needed(host: str, port: int) -> None:
    pids: list[int] = _find_listening_pids(port)
    if not pids:
        return

    print(f"Port {host}:{port} is in use; stopping PIDs {pids}")
    _signal_pids(pids, signal.SIGTERM)
    if _wait_for_port_release(port):
        print(f"Released port {host}:{port}")
        return

    remaining_pids: list[int] = _find_listening_pids(port)
    if remaining_pids:
        print(f"Port {host}:{port} is still in use; force killing PIDs {remaining_pids}")
        _signal_pids(remaining_pids, signal.SIGKILL)

    if _wait_for_port_release(port):
        print(f"Released port {host}:{port}")
        return

    raise RuntimeError(f"Failed to release TCP port {host}:{port}")


def _find_listening_pids(port: int) -> list[int]:
    socket_inodes: set[str] = _find_listening_socket_inodes(port)
    if not socket_inodes:
        return []
    return _find_pids_by_socket_inodes(socket_inodes)


def _find_listening_socket_inodes(port: int) -> set[str]:
    if not _PROC_PATH.exists():
        raise RuntimeError("Cannot inspect listening sockets because /proc is not available")

    target_port_hex: str = f"{port:04X}"
    socket_inodes: set[str] = set()

    # Linux exposes open TCP sockets through /proc/net/tcp* with the local
    # address encoded as hex. Listening sockets use state 0A.
    for tcp_path in (_PROC_PATH / "net" / "tcp", _PROC_PATH / "net" / "tcp6"):
        if not tcp_path.exists():
            continue

        with tcp_path.open("r", encoding="utf-8") as f:
            next(f, None)
            for line in f:
                fields: list[str] = line.split()
                if len(fields) < 10:
                    continue

                local_address: str = fields[1]
                state: str = fields[3]
                inode: str = fields[9]
                _, local_port_hex = local_address.rsplit(":", 1)
                if local_port_hex.upper() == target_port_hex and state == _LISTEN_STATE:
                    socket_inodes.add(inode)

    return socket_inodes


def _find_pids_by_socket_inodes(socket_inodes: set[str]) -> list[int]:
    pids: set[int] = set()

    for proc_dir in _PROC_PATH.iterdir():
        if not proc_dir.name.isdigit():
            continue

        fd_dir: Path = proc_dir / "fd"
        try:
            for fd_path in fd_dir.iterdir():
                try:
                    target: str = os.readlink(fd_path)
                except OSError:
                    continue

                inode: str | None = _extract_socket_inode(target)
                if inode in socket_inodes:
                    pids.add(int(proc_dir.name))
                    break
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            continue

    return sorted(pids)


def _extract_socket_inode(target: str) -> str | None:
    prefix: str = "socket:["
    if not target.startswith(prefix) or not target.endswith("]"):
        return None
    return target[len(prefix) : -1]


def _signal_pids(pids: list[int], sig: signal.Signals) -> None:
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            continue
        except PermissionError as exc:
            raise RuntimeError(f"Permission denied while signaling PID {pid}") from exc


def _wait_for_port_release(port: int) -> bool:
    deadline: float = time.monotonic() + _TERM_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not _find_listening_pids(port):
            return True
        time.sleep(_POLL_INTERVAL_SECONDS)

    return not _find_listening_pids(port)


def _open_startup_browser(url: str) -> None:
    try:
        subprocess.Popen(
            [_STARTUP_BROWSER_COMMAND, "--target", _STARTUP_BROWSER_TARGET, url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        print(
            f"Startup browser '{_STARTUP_BROWSER_COMMAND}' was not found; "
            f"continuing without opening {url}"
        )
    except OSError as exc:
        print(
            f"Failed to launch startup browser '{_STARTUP_BROWSER_COMMAND}': {exc}. "
            f"Continuing without opening {url}"
        )


if __name__ == "__main__":
    main()
