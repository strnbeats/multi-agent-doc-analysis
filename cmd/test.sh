#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
export APP_MODE=mock
exec "$PYTHON_BIN" -m pytest "$@"
