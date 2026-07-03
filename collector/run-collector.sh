#!/usr/bin/env bash

set -euo pipefail

readonly WRAPPER_VERSION="0.1.0"
SCRIPT_PATH=${BASH_SOURCE[0]}
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE=${SCRIPT_PATH%/*} ;;
  *) SCRIPT_BASE=. ;;
esac
readonly SCRIPT_DIR=$(CDPATH= cd -- "$SCRIPT_BASE" && pwd -P)

usage() {
  cat <<'EOF'
Usage: run-collector.sh [OPTIONS]

Run the read-only Oracle compliance collector.

Options:
  --config PATH                Configuration file (default: ./collector.config.yaml)
  --out PATH                   Output directory (default: ./out)
  --only NAME                  Run only a collector/service; repeatable
  --skip NAME                  Skip a collector/service; repeatable
  --dry-run                    Validate configuration and planned collectors only
  --offline-only              Disable OCI collection
  --encryption-key-file PATH   Read encryption key material from PATH
  --collector-bin PATH         Use an explicit collector executable
  --help                       Show this help and exit
  --version                    Show wrapper version and exit

Executable resolution:
  --collector-bin, .venv/bin/collector, PATH collector, local python3 module.
EOF
}

fail() {
  printf 'run-collector.sh: %s\n' "$1" >&2
  exit 2
}

require_value() {
  local option=$1
  if [[ $# -lt 2 || $2 == --* ]]; then
    fail "$option requires a value"
  fi
}

CONFIG_PATH="./collector.config.yaml"
OUTPUT_PATH="./out"
EXPLICIT_COLLECTOR=""
ENCRYPTION_KEY_FILE=""
FORWARD_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      require_value "$@"
      CONFIG_PATH=$2
      shift 2
      ;;
    --out)
      require_value "$@"
      OUTPUT_PATH=$2
      shift 2
      ;;
    --only|--skip)
      require_value "$@"
      FORWARD_ARGS+=("$1" "$2")
      shift 2
      ;;
    --dry-run|--offline-only)
      FORWARD_ARGS+=("$1")
      shift
      ;;
    --encryption-key-file)
      require_value "$@"
      ENCRYPTION_KEY_FILE=$2
      FORWARD_ARGS+=("$1" "$2")
      shift 2
      ;;
    --collector-bin)
      require_value "$@"
      EXPLICIT_COLLECTOR=$2
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    --version)
      printf 'run-collector.sh %s\n' "$WRAPPER_VERSION"
      exit 0
      ;;
    --*)
      fail "Unknown option: $1"
      ;;
    *)
      fail "Unexpected argument: $1"
      ;;
  esac
done

if [[ ! -f "$CONFIG_PATH" || ! -r "$CONFIG_PATH" ]]; then
  fail "Configuration file not found or unreadable: $CONFIG_PATH"
fi
if [[ -n "$ENCRYPTION_KEY_FILE" && ( ! -f "$ENCRYPTION_KEY_FILE" || ! -r "$ENCRYPTION_KEY_FILE" ) ]]; then
  fail "Encryption key file is not readable: $ENCRYPTION_KEY_FILE"
fi

COLLECTOR_COMMAND=()
USE_LOCAL_MODULE=false

if [[ -n "$EXPLICIT_COLLECTOR" ]]; then
  if [[ "$EXPLICIT_COLLECTOR" == */* ]]; then
    [[ -f "$EXPLICIT_COLLECTOR" && -x "$EXPLICIT_COLLECTOR" ]] \
      || fail "Collector executable is not usable: $EXPLICIT_COLLECTOR"
    COLLECTOR_COMMAND=("$EXPLICIT_COLLECTOR")
  else
    RESOLVED_COLLECTOR=$(command -v "$EXPLICIT_COLLECTOR" 2>/dev/null || true)
    [[ -n "$RESOLVED_COLLECTOR" && -x "$RESOLVED_COLLECTOR" ]] \
      || fail "Collector executable is not usable: $EXPLICIT_COLLECTOR"
    COLLECTOR_COMMAND=("$RESOLVED_COLLECTOR")
  fi
elif [[ -f "$SCRIPT_DIR/../.venv/bin/collector" && -x "$SCRIPT_DIR/../.venv/bin/collector" ]]; then
  COLLECTOR_COMMAND=("$SCRIPT_DIR/../.venv/bin/collector")
else
  RESOLVED_COLLECTOR=$(command -v collector 2>/dev/null || true)
  if [[ -n "$RESOLVED_COLLECTOR" && -x "$RESOLVED_COLLECTOR" ]]; then
    COLLECTOR_COMMAND=("$RESOLVED_COLLECTOR")
  else
    RESOLVED_PYTHON=$(command -v python3 2>/dev/null || true)
    if [[ -n "$RESOLVED_PYTHON" && -x "$RESOLVED_PYTHON" && -d "$SCRIPT_DIR/src" ]]; then
      COLLECTOR_COMMAND=("$RESOLVED_PYTHON" "-m" "oracle_collector")
      USE_LOCAL_MODULE=true
    else
      fail "No usable collector executable or python3 found"
    fi
  fi
fi

RUN_ARGS=("run" "--config" "$CONFIG_PATH" "--out" "$OUTPUT_PATH")
if [[ ${#FORWARD_ARGS[@]} -gt 0 ]]; then
  RUN_ARGS+=("${FORWARD_ARGS[@]}")
fi

if [[ "$USE_LOCAL_MODULE" == true ]]; then
  export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
fi

exec "${COLLECTOR_COMMAND[@]}" "${RUN_ARGS[@]}"
