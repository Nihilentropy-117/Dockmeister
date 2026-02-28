"""Container shell access using app.suspend() for PTY passthrough."""

from __future__ import annotations

import subprocess
import sys


def shell_into_container(container_id: str) -> None:
    result = subprocess.run(
        ["docker", "exec", "-it", container_id, "/bin/bash"],
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        subprocess.run(
            ["docker", "exec", "-it", container_id, "/bin/sh"],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
