#!/usr/bin/env bash
# Script to run ScreenSense test suite
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Qt uses offscreen platform so UI tests run without an active X11 display
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

# Use virtual environment python if available, otherwise fallback to python3
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "Running ScreenSense test suite with $($PYTHON --version)..."
"$PYTHON" -m pytest screensense/tests/ "$@"

