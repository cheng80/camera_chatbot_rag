#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

HOST="127.0.0.1"
PORT="8010"
APP_MODULE="${CAMERA_APP_MODULE:-backend.app.main:app}"

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}"
fi

if [[ -x ".venv/bin/uvicorn" ]]; then
  exec .venv/bin/uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}"
fi

echo "Neither uv nor .venv/bin/uvicorn is available." >&2
exit 1
