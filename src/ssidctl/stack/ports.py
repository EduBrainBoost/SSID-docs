"""2-phase port selection and health checking."""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request


class PortError(RuntimeError):
    """Raised when no free port is available."""


def _is_listening(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is currently accepting connections."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    finally:
        sock.close()


def _http_get_status(url: str, timeout: float = 5.0) -> int | None:
    """Attempt HTTP GET and return status code, or None on failure."""
    try:
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status
    except Exception:
        return None


def find_free_port(candidates: list[int], host: str = "127.0.0.1") -> int:
    """Phase 1: Find first non-listening port from candidates list.

    Args:
        candidates: Ordered list of port numbers to try.
        host: Host to probe (default: 127.0.0.1).

    Returns:
        First port not currently listening.

    Raises:
        PortError: If all candidates are occupied or list is empty.
    """
    if not candidates:
        raise PortError("no candidates provided")

    for port in candidates:
        if not _is_listening(port, host):
            return port

    raise PortError(f"all candidates occupied: {candidates}")


def wait_for_health(
    url: str,
    expect_status: int,
    max_retries: int = 30,
    backoff: float = 1.0,
) -> bool:
    """Phase 2: Wait for health endpoint to respond with expected status.

    Uses bounded exponential backoff.

    Args:
        url: Health check URL.
        expect_status: Expected HTTP status code.
        max_retries: Maximum number of attempts.
        backoff: Initial backoff in seconds (doubles each retry, capped at 10s).

    Returns:
        True if health check passed, False if all retries exhausted.
    """
    delay = backoff
    for _ in range(max_retries):
        status = _http_get_status(url)
        if status == expect_status:
            return True
        time.sleep(delay)
        delay = min(delay * 2, 10.0)
    return False
