#!/usr/bin/env bash
# MHR-Hybrid one-click launcher (Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[X] python3 is not installed or not on PATH." >&2
  exit 1
fi

if [ ! -f "config.json" ]; then
  echo "[X] Missing required file: config.json" >&2
  echo "    Hint: cp config.example.json config.json" >&2
  exit 1
fi

if ! python3 -c "import src.app" >/dev/null 2>&1; then
  echo "[*] Installing dependencies from requirements.txt ..."
  if ! python3 -m pip install -r requirements.txt; then
    echo "[X] Dependency install failed. Install manually: python3 -m pip install -r requirements.txt" >&2
    exit 1
  fi
fi

exec python3 bootstrap.py "$@"
