#!/bin/bash

set -euo pipefail

load_project_env() {
  local root_dir="$1"
  local env_file="${2:-$root_dir/.env}"

  if [[ ! -f "$env_file" ]]; then
    return 0
  fi

  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}
