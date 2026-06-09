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
URL="http://${HOST}:${PORT}"
APP_MODULE="${CAMERA_APP_MODULE:-backend.app.main:app}"
SERVER_LOG="${CAMERA_TUNNEL_SERVER_LOG:-.quick-tunnel-uvicorn.log}"
SERVER_PID=""

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed or not on PATH." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "Stopping local uvicorn server pid ${SERVER_PID}"
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}

health_check() {
  curl -fsS "${URL}/api/health" >/dev/null 2>&1
}

start_local_server() {
  if command -v uv >/dev/null 2>&1; then
    uv run uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" >>"${SERVER_LOG}" 2>&1 &
  elif [[ -x ".venv/bin/uvicorn" ]]; then
    .venv/bin/uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" >>"${SERVER_LOG}" 2>&1 &
  else
    echo "Neither uv nor .venv/bin/uvicorn is available." >&2
    exit 1
  fi
  SERVER_PID="$!"
  trap cleanup EXIT INT TERM
}

if health_check; then
  echo "Local app is already responding at ${URL}"
else
  echo "Local app is not responding at ${URL}/api/health."
  echo "Starting uvicorn ${APP_MODULE} on ${HOST}:${PORT}"
  echo "Server log: ${SERVER_LOG}"
  start_local_server

  for _ in {1..40}; do
    if health_check; then
      break
    fi
    sleep 0.5
  done

  if ! health_check; then
    echo "Local app did not become healthy at ${URL}/api/health." >&2
    echo "Check server log: ${SERVER_LOG}" >&2
    exit 1
  fi
fi

echo "Starting Cloudflare quick tunnel for ${URL}"
echo "Public URL will appear below as https://*.trycloudflare.com"
cloudflared tunnel --url "${URL}"
