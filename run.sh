#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
else
    PYTHON_BIN="python3"
fi

if [ -d ".venv/lib" ]; then
    for d in .venv/lib/python*/site-packages; do
        if [ -d "$d" ]; then
            export PYTHONPATH="${d}:${PYTHONPATH}"
        fi
    done
fi

"$PYTHON_BIN" main_gui.py
