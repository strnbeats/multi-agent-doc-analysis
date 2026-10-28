#!/usr/bin/env sh
set -eu

MODE="${1:-real}"
if [ "$MODE" != "real" ] && [ "$MODE" != "mock" ]; then
  echo "Использование: ./cmd/run.sh [real|mock]" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
export APP_MODE="$MODE"

if [ "$MODE" = "mock" ] && [ -z "${DATABASE_PATH:-}" ]; then
  export DATABASE_PATH="data/mock.db"
fi

if [ "${RELOAD:-0}" = "1" ]; then
  exec "$PYTHON_BIN" -m uvicorn multi_agent_docs.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" --reload
fi

exec "$PYTHON_BIN" -m uvicorn multi_agent_docs.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
