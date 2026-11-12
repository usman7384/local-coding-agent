"""Run a shell command inside a throwaway, locked-down Docker container."""

import os
import subprocess
from pathlib import Path

IMAGE = "agent-reliability-sandbox:1"  # built from docker/Dockerfile: python:3.12 + pytest, user "agent"
READ_ONLY = ["tests", "pytest.ini"]    # guardrail: the agent can run the tests but never change them
TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "30"))  # seconds per command


def run(workdir: Path, command: str, timeout: int = TIMEOUT, network: bool = False) -> tuple[int, str]:
    """Run `command` in a new container that can only see `workdir` (mounted at /work).

    The container has no network (unless asked, for a setup step that installs packages), 1 CPU, 768 MB of memory,
    runs as a non-root user, and is deleted as soon as the command finishes. The tests and pytest.ini are mounted
    read-only on top; a virtualenv in /work/.venv, if any, comes first on the PATH. Returns (exit code, output).
    """
    locked = [arg for name in READ_ONLY if (workdir / name).exists()
              for arg in ("-v", f"{(workdir / name).resolve()}:/work/{name}:ro")]
    docker = [
        "docker", "run", "--rm", "--network", "bridge" if network else "none", "--cpus", "1", "--memory", "768m",
        "--user", "agent", "-e", "PYTEST_ADDOPTS=--tb=short", "-e", "PATH=/work/.venv/bin:/usr/local/bin:/usr/bin:/bin",
        "-v", f"{workdir.resolve()}:/work", *locked, "-w", "/work", IMAGE,
        "timeout", str(timeout), "bash", "-c", command,
    ]
    try:
        done = subprocess.run(docker, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, done.stdout + done.stderr
