"""Run a shell command inside a throwaway, locked-down Docker container."""

import subprocess
from pathlib import Path

IMAGE = "agent-reliability-sandbox:1"  # built from docker/Dockerfile: python:3.12 + pytest, user "agent"


def run(workdir: Path, command: str, timeout: int = 30) -> tuple[int, str]:
    """Run `command` in a new container that can only see `workdir` (mounted at /work).

    The container has no network, 1 CPU, 768 MB of memory, runs as a non-root user,
    and is deleted as soon as the command finishes. Returns (exit code, output).
    """
    docker = [
        "docker", "run", "--rm", "--network", "none", "--cpus", "1", "--memory", "768m",
        "--user", "agent", "-e", "PYTEST_ADDOPTS=--tb=short",
        "-v", f"{workdir.resolve()}:/work", "-w", "/work", IMAGE,
        "timeout", str(timeout), "bash", "-c", command,
    ]
    try:
        done = subprocess.run(docker, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, done.stdout + done.stderr
