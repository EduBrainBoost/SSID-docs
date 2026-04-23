"""Windows-native process start/stop for stack components."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class StopError(Exception):
    """Raised when process stop fails."""


class ProcessRunner:
    """Mockable process runner for stack components.

    All process operations go through this class so tests can
    inject mocks without starting real processes.
    """

    def start(
        self,
        name: str,
        cmd: list[str],
        workdir: str | Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        """Start a component process."""
        # Resolve command to full path (handles .cmd/.bat on Windows)
        resolved = shutil.which(cmd[0])
        if resolved:
            cmd = [resolved] + cmd[1:]
        return subprocess.Popen(
            cmd,
            cwd=str(workdir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            if sys.platform == "win32"
            else 0,
        )

    def stop(
        self,
        proc: subprocess.Popen,
        name: str,
        grace_seconds: float = 10.0,
    ) -> int | None:
        """Stop a component process using Windows-native strategy.

        Strategy:
        1. If already exited -> return exit code (no-op).
        2. Graceful: proc.terminate().
        3. Wait up to grace_seconds.
        4. Force: taskkill /T /F /PID {pid}.
        """
        if proc.poll() is not None:
            return proc.returncode

        proc.terminate()
        try:
            return proc.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass

        # Force kill via taskkill (Windows) or SIGKILL (Unix)
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            proc.kill()

        try:
            return proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            return None
