#!/usr/bin/env python3
"""First-run bootstrap: install deps, validate config, and start app."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"
CONFIG = ROOT / "config.json"


def ensure_dependencies() -> None:
    try:
        importlib.import_module("src.app")
    except ModuleNotFoundError:
        print("[*] Missing dependencies detected. Installing from requirements.txt ...")
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(
                f"[X] Dependency install failed. Run {sys.executable} -m pip install -r requirements.txt",
                file=sys.stderr,
            )
            raise SystemExit(result.returncode)


def ensure_config() -> None:
    if not CONFIG.exists():
        print("[X] Missing required file: config.json", file=sys.stderr)
        print("    Hint: copy config.example.json to config.json", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    os.chdir(ROOT)
    ensure_config()
    ensure_dependencies()
    raise SystemExit(subprocess.call([sys.executable, "main.py", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
