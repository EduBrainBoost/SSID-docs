"""Stub Provider for testing - executes simple commands without interaction.

This provider is used when no interactive CLI providers are available.
It simply executes shell commands and returns the output.
"""

from __future__ import annotations

import subprocess
<<<<<<< HEAD
=======
import shutil
>>>>>>> origin/chore/artifact-cleanup-20260331
from pathlib import Path


def execute_stub_command(prompt: str, cwd: Path | None = None, timeout: int = 60) -> tuple[bool, str, str]:
    """Execute a simple command via shell.
<<<<<<< HEAD

=======
    
>>>>>>> origin/chore/artifact-cleanup-20260331
    For testing purposes, this provider interprets the prompt as a shell command
    or returns a canned success response for task-like prompts.
    """
    if prompt.startswith("!"):
        cmd = prompt[1:]
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
<<<<<<< HEAD

=======
    
>>>>>>> origin/chore/artifact-cleanup-20260331
    return True, f"Stub execution completed for: {prompt[:100]}", ""
