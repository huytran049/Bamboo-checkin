#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT_DIR/scripts/runtime_env.sh"
load_project_env "$ROOT_DIR"

PORT="${PORT:-5001}"
HOST="${HOST:-0.0.0.0}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-business-card}"
export RAG_V2_EMBED_MODEL="${RAG_V2_EMBED_MODEL:-bge-m3}"
export RAG_V2_GENERATE_MODEL="${RAG_V2_GENERATE_MODEL:-}"
export RAG_V2_PREBUILD_INDEX="${RAG_V2_PREBUILD_INDEX:-1}"
export OCR_USE_REDIS="${OCR_USE_REDIS:-0}"
export FACE_USE_REDIS="${FACE_USE_REDIS:-0}"
export QA_TTS_GTTS_LANG="${QA_TTS_GTTS_LANG:-vi}"
export QA_TTS_GTTS_TLD="${QA_TTS_GTTS_TLD:-com}"
export QA_TTS_SEGMENT_PAUSE_MS="${QA_TTS_SEGMENT_PAUSE_MS:-140}"
export QA_TTS_PLAYBACK_RATE="${QA_TTS_PLAYBACK_RATE:-1.25}"
PID_DIR="$ROOT_DIR/.run"
PID_FILE="$PID_DIR/app-${PORT}.pid"
WORKER_PID_FILE="$PID_DIR/ocr_redis_worker.pid"
FACE_WORKER_PID_FILE="$PID_DIR/face_redis_worker.pid"
OLLAMA_PID_FILE="$PID_DIR/ollama.pid"
REDIS_PID_FILE="$PID_DIR/redis.pid"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_HEALTH_URL="${OLLAMA_HOST%/}/api/tags"

mkdir -p "$PID_DIR"

cleanup_stale_pid() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "App is already running on PID $pid (port $PORT)."
      exit 1
    fi
    rm -f "$PID_FILE"
  fi
}

free_port_if_needed() {
  local pids
  pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "${pids:-}" ]]; then
    return
  fi

  echo "Port $PORT is busy. Stopping existing process(es): $pids"
  kill $pids 2>/dev/null || true
  sleep 1

  local survivors
  survivors="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${survivors:-}" ]]; then
    echo "Force killing remaining process(es): $survivors"
    kill -9 $survivors 2>/dev/null || true
  fi
}

cleanup_stale_pid
free_port_if_needed

pick_cmd_path() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi
  echo "Required command '$name' was not found in PATH." >&2
  exit 1
}

pick_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    echo "$PYTHON_BIN"
    return 0
  fi

  local candidates=(
    "$ROOT_DIR/.venv_lora/bin/python"
    "$(command -v python3 || true)"
    "$(command -v python || true)"
  )

  local bin
  for bin in "${candidates[@]}"; do
    if [[ -z "${bin:-}" || ! -x "$bin" ]]; then
      continue
    fi
    if "$bin" -c "import flask" >/dev/null 2>&1; then
      echo "$bin"
      return 0
    fi
  done

  echo "No Python interpreter with Flask installed was found." >&2
  exit 1
}

probe_ollama_bin() {
  local bin="$1"
  [[ -n "${bin:-}" && -x "$bin" ]] || return 1

  "$bin" --version >/dev/null 2>&1 &
  local pid=$!
  local attempt
  for attempt in {1..50}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid"
      return $?
    fi
    sleep 0.1
  done

  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  return 1
}

pick_ollama_bin() {
  local candidates=()

  if [[ -n "${OLLAMA_BIN:-}" ]]; then
    candidates+=("$OLLAMA_BIN")
  fi

  if command -v ollama >/dev/null 2>&1; then
    candidates+=("$(command -v ollama)")
  fi

  candidates+=(
    "$ROOT_DIR/.tmp_ollama_0204rc2/Ollama.app/Contents/Resources/ollama"
    "$ROOT_DIR/.tmp_ollama_0182/ollama/0.18.2/bin/ollama"
  )

  local bin
  for bin in "${candidates[@]}"; do
    if probe_ollama_bin "$bin"; then
      echo "$bin"
      return 0
    fi
    if [[ -n "${bin:-}" && -x "$bin" ]]; then
      echo "Skipping unusable Ollama binary: $bin" >&2
    fi
  done

  echo "No working Ollama binary was found. Set OLLAMA_BIN to a valid binary." >&2
  exit 1
}

start_ollama_if_needed() {
  if curl -fsS "$OLLAMA_HEALTH_URL" >/dev/null 2>&1; then
    echo "Ollama is already running."
    return 0
  fi

  local ollama_bin
  ollama_bin="$(pick_ollama_bin)"
  echo "Starting ollama serve with: $ollama_bin"
  "$ollama_bin" serve >/tmp/bamboo_ollama.log 2>&1 &
  local ollama_pid=$!
  echo "$ollama_pid" > "$OLLAMA_PID_FILE"

  local attempt
  for attempt in $(seq 1 20); do
    if curl -fsS "$OLLAMA_HEALTH_URL" >/dev/null 2>&1; then
      echo "Ollama is ready."
      return 0
    fi
    sleep 1
  done

  echo "Ollama failed to start. Check /tmp/bamboo_ollama.log" >&2
  exit 1
}

ollama_model_exists() {
  local model_name="$1"
  local ollama_bin="$2"
  [[ -n "${model_name:-}" ]] || return 1

  local installed
  installed="$("$ollama_bin" list 2>/dev/null | awk 'NR>1 {print $1}')"
  if printf '%s\n' "$installed" | grep -Fx "$model_name" >/dev/null 2>&1; then
    return 0
  fi
  if printf '%s\n' "$installed" | grep -Fx "${model_name}:latest" >/dev/null 2>&1; then
    return 0
  fi
  printf '%s\n' "$installed" | grep -E "^${model_name//./\\.}:" >/dev/null 2>&1
}

ensure_ollama_model() {
  local model_name="$1"
  local label="$2"
  local ollama_bin="$3"
  [[ -n "${model_name:-}" ]] || return 0

  if ollama_model_exists "$model_name" "$ollama_bin"; then
    echo "$label model is ready: $model_name"
    return 0
  fi

  echo "Pulling missing $label model: $model_name"
  "$ollama_bin" pull "$model_name"
}

ensure_ollama_models_ready() {
  local ollama_bin
  ollama_bin="$(pick_ollama_bin)"

  if [[ "${OCR_USE_REDIS}" == "1" ]]; then
    ensure_ollama_model "$OLLAMA_MODEL" "OCR" "$ollama_bin"
  else
    echo "Skipping OCR model bootstrap because OCR_USE_REDIS=${OCR_USE_REDIS}."
  fi
  ensure_ollama_model "$RAG_V2_EMBED_MODEL" "RAG v2 embed" "$ollama_bin"
  ensure_ollama_model "$RAG_V2_GENERATE_MODEL" "RAG v2 generate" "$ollama_bin"
}

start_redis_if_needed() {
  if redis-cli ping >/dev/null 2>&1; then
    echo "Redis is already running."
    return 0
  fi

  local redis_bin
  redis_bin="$(pick_cmd_path redis-server)"

  echo "Starting Redis..."
  "$redis_bin" --save "" --appendonly no --daemonize yes --pidfile "$REDIS_PID_FILE" --logfile /tmp/bamboo_redis.log

  local attempt
  for attempt in $(seq 1 20); do
    if redis-cli ping >/dev/null 2>&1; then
      echo "Redis is ready."
      return 0
    fi
    sleep 1
  done

  echo "Redis failed to start. Check /tmp/bamboo_redis.log" >&2
  exit 1
}

start_redis_workers_if_needed() {
  local enable_ocr_redis="${OCR_USE_REDIS:-1}"
  local enable_face_redis="${FACE_USE_REDIS:-1}"

  if [[ "$enable_ocr_redis" != "1" && "$enable_face_redis" != "1" ]]; then
    echo "Redis workers are disabled by env. Skipping worker startup."
    return 0
  fi

  start_redis_if_needed

  local swift_bin
  swift_bin="$(pick_cmd_path swift)"

  if [[ "$enable_ocr_redis" == "1" ]]; then
    if pgrep -f "helpers/ocr_redis_worker.py" >/dev/null 2>&1; then
      echo "Python OCR Redis worker is already running."
    else
      echo "Starting Python OCR Redis worker (Swift OCR backend, model: $OLLAMA_MODEL)..."
      cd "$ROOT_DIR"
      OCR_USE_REDIS="$enable_ocr_redis" FACE_USE_REDIS="$enable_face_redis" OLLAMA_MODEL="$OLLAMA_MODEL" "$PYTHON_BIN" helpers/ocr_redis_worker.py >/tmp/bamboo_redis_worker.log 2>&1 &
      local worker_pid=$!
      echo "$worker_pid" > "$WORKER_PID_FILE"
      sleep 1
      if ! kill -0 "$worker_pid" 2>/dev/null; then
        echo "Python OCR Redis worker failed to start. Check /tmp/bamboo_redis_worker.log" >&2
        exit 1
      fi
    fi
  else
    echo "OCR Redis worker disabled (OCR_USE_REDIS=$enable_ocr_redis)."
  fi

  if [[ "$enable_face_redis" != "1" ]]; then
    echo "Face Redis worker enable (FACE_USE_REDIS=$enable_face_redis)."
    return 0
  fi

  if pgrep -f "swift .*workers_swift/face_redis_worker.swift" >/dev/null 2>&1 || pgrep -f "workers_swift/face_redis_worker.swift" >/dev/null 2>&1; then
    echo "Swift face Redis worker is already running."
    return 0
  fi

  echo "Starting Swift face Redis worker..."
  FACE_USE_REDIS="$enable_face_redis" OCR_USE_REDIS="$enable_ocr_redis" "$swift_bin" workers_swift/face_redis_worker.swift >/tmp/bamboo_face_redis_worker.log 2>&1 &
  local face_worker_pid=$!
  echo "$face_worker_pid" > "$FACE_WORKER_PID_FILE"
  sleep 1
  if ! kill -0 "$face_worker_pid" 2>/dev/null; then
    echo "Swift face Redis worker failed to start. Check /tmp/bamboo_face_redis_worker.log" >&2
    exit 1
  fi
}

ensure_rag_v2_index_ready() {
  if [[ "${RAG_V2_PREBUILD_INDEX}" != "1" ]]; then
    echo "RAG v2 prebuild disabled (RAG_V2_PREBUILD_INDEX=$RAG_V2_PREBUILD_INDEX)."
    return 0
  fi

  echo "Checking RAG v2 index status..."
  cd "$ROOT_DIR"
  "$PYTHON_BIN" - <<'PY'
from services.rag_v2.service import get_index_status
from services.rag_v2.indexer import build_index
from pathlib import Path

data_dir = Path("Rag_data")
status = get_index_status()
if not status.get("is_ready"):
    print("Building rag_v2 index...")
    build_index(data_dir, force=True)
    status = get_index_status()

print("RAG v2 index ready:", status)
PY
}

ensure_qa_tts_ready() {
  echo "Warming up QA TTS..."
  cd "$ROOT_DIR"
  "$PYTHON_BIN" - <<'PY'
from services.qa_tts_service import warmup_qa_tts

warmup_qa_tts()
print("QA TTS warmup done.")
PY
}

cd "$ROOT_DIR"
PYTHON_BIN="$(pick_python_bin)"
start_ollama_if_needed
ensure_ollama_models_ready
start_redis_workers_if_needed

export HOST="$HOST"
export PORT="$PORT"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"
export FLASK_RELOADER="${FLASK_RELOADER:-0}"
export OCR_USE_REDIS="${OCR_USE_REDIS:-0}"
export FACE_USE_REDIS="${FACE_USE_REDIS:-0}"
export OLLAMA_HOST="$OLLAMA_HOST"
export OLLAMA_MODEL="$OLLAMA_MODEL"
export RAG_V2_EMBED_MODEL="$RAG_V2_EMBED_MODEL"
export RAG_V2_GENERATE_MODEL="$RAG_V2_GENERATE_MODEL"
export QA_TTS_GTTS_LANG="$QA_TTS_GTTS_LANG"
export QA_TTS_GTTS_TLD="$QA_TTS_GTTS_TLD"
export QA_TTS_SEGMENT_PAUSE_MS="$QA_TTS_SEGMENT_PAUSE_MS"
export QA_TTS_PLAYBACK_RATE="$QA_TTS_PLAYBACK_RATE"

ensure_rag_v2_index_ready
ensure_qa_tts_ready

"$PYTHON_BIN" application.py &
APP_PID=$!
echo "$APP_PID" > "$PID_FILE"

cleanup() {
  if kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"

  if [[ -f "$WORKER_PID_FILE" ]]; then
    local worker_pid
    worker_pid="$(cat "$WORKER_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${worker_pid:-}" ]] && kill -0 "$worker_pid" 2>/dev/null; then
      kill "$worker_pid" 2>/dev/null || true
    fi
    rm -f "$WORKER_PID_FILE"
  fi

  if [[ -f "$FACE_WORKER_PID_FILE" ]]; then
    local face_worker_pid
    face_worker_pid="$(cat "$FACE_WORKER_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${face_worker_pid:-}" ]] && kill -0 "$face_worker_pid" 2>/dev/null; then
      kill "$face_worker_pid" 2>/dev/null || true
    fi
    rm -f "$FACE_WORKER_PID_FILE"
  fi

  if [[ -f "$OLLAMA_PID_FILE" ]]; then
    local ollama_pid
    ollama_pid="$(cat "$OLLAMA_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${ollama_pid:-}" ]] && kill -0 "$ollama_pid" 2>/dev/null; then
      kill "$ollama_pid" 2>/dev/null || true
    fi
    rm -f "$OLLAMA_PID_FILE"
  fi

  if [[ -f "$REDIS_PID_FILE" ]]; then
    local redis_pid
    redis_pid="$(cat "$REDIS_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${redis_pid:-}" ]] && kill -0 "$redis_pid" 2>/dev/null; then
      kill "$redis_pid" 2>/dev/null || true
    fi
    rm -f "$REDIS_PID_FILE"
  fi
}

trap cleanup EXIT INT TERM HUP

wait "$APP_PID"
