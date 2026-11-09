from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _npm() -> str:
    executable = shutil.which("npm.cmd") or shutil.which("npm")
    if executable is None:
        raise SystemExit("npm was not found on PATH.")
    return executable


def main() -> None:
    web = subprocess.Popen(
        [_npm(), "--prefix", "web", "run", "dev"],
        cwd=ROOT,
    )
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT / "api",
    )

    def stop(*_args: object) -> None:
        for process in (api, web):
            if process.poll() is None:
                process.terminate()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        api.wait()
    finally:
        if web.poll() is None:
            web.terminate()
        if api.poll() is None:
            api.terminate()
        if os.name == "nt":
            web.wait(timeout=10)
            api.wait(timeout=10)


if __name__ == "__main__":
    main()
