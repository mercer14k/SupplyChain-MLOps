"""Isolated backend + worker process supervisor for browser tests."""

import os
import signal
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
children = []


def stop(*_):
    for child in children:
        child.terminate()
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    subprocess.run([sys.executable, "-m", "scml.cli", "drain"], check=True)
    children.append(subprocess.Popen([sys.executable, "-m", "scml.cli", "worker"]))
    children.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8019",
            ]
        )
    )
    children[-1].wait()
    stop()
