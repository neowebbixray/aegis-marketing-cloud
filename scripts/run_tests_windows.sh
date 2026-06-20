#!/usr/bin/env bash
cd "$(dirname "$0")/.."

# ----------------------------------------------------------
# Windows‑specific CI test runner for Aegis Marketing Cloud.
# ----------------------------------------------------------
# Usage (inside the repo root):
#   ./scripts/run_tests_windows.sh
#
# The script assumes a recent Python 3.12 installation is
# available at the default Windows path. Adjust PYTHON variable
# if your installation lives elsewhere.
# ----------------------------------------------------------

# Path to the python executable (override via env var if needed)
PYTHON="${PYTHON:-/c/Program Files/Python312/python.exe}"
# If the default Windows Python path does not exist, fall back to the system python (Linux/macOS)
if [ ! -f "$PYTHON" ]; then
  PYTHON="python3"
fi

# Upgrade pip and install the project in editable mode with dev deps.
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install --user -e .[dev]

# Run the test suite. pytest automatically skips tests marked
# with `skipif(sys.platform.startswith("win"))`.
# Using -n auto enables parallel execution via pytest‑xdist.
"$PYTHON" -m pytest -k "not integration" "$@"
