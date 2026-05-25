#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT_DIR/scripts/runtime_env.sh"
load_project_env "$ROOT_DIR"

PORT="${PORT:-5001}"
PID_FILE="$ROOT_DIR/.run/app-${PORT}.pid"
WORKER_PID_FILE="$ROOT_DIR/.run/ocr_redis_worker.pid"
FACE_WORKER_PID_FILE="$ROOT_DIR/.run/face_redis_worker.pid"
OLLAMA_PID_FILE="$ROOT_DIR/.run/ollama.pid"

stop_pid() {
  local pid="$1"
  if [[ -z "${pid:-}" ]]; then
    return
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
}

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID"
  rm -f "$PID_FILE"
fi

if [[ -f "$WORKER_PID_FILE" ]]; then
  PID="$(cat "$WORKER_PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID"
  rm -f "$WORKER_PID_FILE"
fi

if [[ -f "$FACE_WORKER_PID_FILE" ]]; then
  PID="$(cat "$FACE_WORKER_PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID"
  rm -f "$FACE_WORKER_PID_FILE"
fi

if [[ -f "$OLLAMA_PID_FILE" ]]; then
  PID="$(cat "$OLLAMA_PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID"
  rm -f "$OLLAMA_PID_FILE"
fi

PORT_PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "${PORT_PIDS:-}" ]]; then
  for pid in $PORT_PIDS; do
    stop_pid "$pid"
  done
fi

echo "Port $PORT is now free."
