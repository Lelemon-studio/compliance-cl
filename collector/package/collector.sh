#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH=${BASH_SOURCE[0]}
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE=${SCRIPT_PATH%/*} ;;
  *) SCRIPT_BASE=. ;;
esac
readonly BUNDLE_DIR=$(CDPATH= cd -- "$SCRIPT_BASE" && pwd -P)
readonly PROFILE_DIR="$BUNDLE_DIR/profiles"
readonly CONFIG_DIR="$BUNDLE_DIR/customer-config"
readonly RUNTIME_DIR="$BUNDLE_DIR/.runtime"
readonly DEFAULT_CONFIG="$CONFIG_DIR/collector.config.yaml"

usage() {
  cat <<'EOF'
Usage: ./collector.sh COMMAND [OPTIONS]

Commands:
  list-profiles                   List bundled config templates
  init --profile NAME [OPTIONS]   Create a customer-owned config copy
  verify                          Verify delivered file checksums
  doctor [--config PATH]          Validate package, config, runtime, and dry-run
  run [COLLECTOR OPTIONS]         Validate and execute the collector
  version                         Show bundle version and delivery mode
  help                            Show this help

Init options:
  --profile NAME                  Profile without .yaml (required)
  --environment NAME              Write customer-config/NAME.yaml
  --config PATH                   Write an explicit config path
  --force                         Replace an existing customer config

Run defaults:
  --config customer-config/collector.config.yaml
  --out out/
EOF
}

fail() {
  printf 'collector.sh: %s\n' "$1" >&2
  exit 2
}

metadata_value() {
  local key=$1
  sed -n "s/^${key}=//p" "$BUNDLE_DIR/BUNDLE-METADATA" | head -n 1
}

verify_bundle() {
  [[ -f "$BUNDLE_DIR/SHA256SUMS" ]] || fail "Integrity manifest is missing"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$BUNDLE_DIR" && sha256sum -c SHA256SUMS >/dev/null) \
      || fail "Bundle integrity verification failed"
  elif command -v shasum >/dev/null 2>&1; then
    (cd "$BUNDLE_DIR" && shasum -a 256 -c SHA256SUMS >/dev/null) \
      || fail "Bundle integrity verification failed"
  else
    fail "sha256sum or shasum is required for integrity verification"
  fi
}

list_profiles() {
  (
    cd "$PROFILE_DIR"
    find . -type f -name '*.yaml' -print |
      sed 's#^\./##; s#\.yaml$##' |
      LC_ALL=C sort
  )
}

valid_profile() {
  local profile=$1
  [[ -n "$profile" ]] || return 1
  case "$profile" in
    /*|*..*|*//*|*[^A-Za-z0-9_/-]*) return 1 ;;
  esac
  [[ -f "$PROFILE_DIR/$profile.yaml" ]]
}

valid_environment() {
  local environment=$1
  [[ -n "$environment" && "$environment" != "." && "$environment" != ".." ]] || return 1
  case "$environment" in
    *[^A-Za-z0-9._-]*) return 1 ;;
  esac
  return 0
}

init_config() {
  local profile=""
  local environment=""
  local environment_set=false
  local config_path=""
  local force=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        [[ $# -ge 2 && -n $2 && $2 != --* ]] || fail "--profile requires a value"
        profile=$2
        shift 2
        ;;
      --environment)
        [[ $# -ge 2 && $2 != --* ]] || fail "--environment requires a value"
        environment=$2
        environment_set=true
        shift 2
        ;;
      --config)
        [[ $# -ge 2 && -n $2 && $2 != --* ]] || fail "--config requires a value"
        config_path=$2
        shift 2
        ;;
      --force)
        force=true
        shift
        ;;
      *) fail "Unknown init option: $1" ;;
    esac
  done

  valid_profile "$profile" || fail "Unknown or unsafe profile: $profile"
  if [[ "$environment_set" == true ]]; then
    valid_environment "$environment" || fail "Unsafe environment name: $environment"
  fi
  if [[ "$environment_set" == true && -n "$config_path" ]]; then
    fail "Use either --environment or --config, not both"
  fi
  if [[ -z "$config_path" ]]; then
    if [[ "$environment_set" == true ]]; then
      config_path="$CONFIG_DIR/$environment.yaml"
    else
      config_path=$DEFAULT_CONFIG
    fi
  fi

  if [[ -e "$config_path" && "$force" != true ]]; then
    fail "Configuration already exists (use --force): $config_path"
  fi
  mkdir -p "${config_path%/*}"
  cp "$PROFILE_DIR/$profile.yaml" "$config_path"
  chmod 0600 "$config_path"
  printf 'Configuration created: %s\n' "$config_path"
  printf 'Next: replace every [REPLACE_...] value, then run doctor.\n'
}

resolve_python() {
  local candidate=${COLLECTOR_PYTHON:-python3}
  if [[ "$candidate" == */* ]]; then
    [[ -f "$candidate" && -x "$candidate" ]] || fail "Python executable is not usable: $candidate"
    printf '%s\n' "$candidate"
    return
  fi
  command -v "$candidate" 2>/dev/null || fail "Python 3.9+ was not found"
}

ensure_runtime() {
  local python_bin
  local version
  local mode
  local extras
  local pip_extra=""
  local app_wheel
  local wheel_spec
  local marker

  python_bin=$(resolve_python)
  "$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
    || fail "Python 3.9 or newer is required"

  version=$(metadata_value version)
  mode=$(metadata_value mode)
  extras=$(metadata_value extras)
  marker="$RUNTIME_DIR/.installed-${version}-${mode}-${extras}"
  if [[ -x "$RUNTIME_DIR/venv/bin/collector" && -f "$marker" ]]; then
    return
  fi

  rm -rf "$RUNTIME_DIR"
  mkdir -p "$RUNTIME_DIR"
  "$python_bin" -m venv "$RUNTIME_DIR/venv" || fail "Unable to create private Python runtime"

  set -- "$BUNDLE_DIR"/wheelhouse/oracle_compliance_collector-*.whl
  [[ $# -eq 1 && -f "$1" ]] || fail "Application wheel is missing or ambiguous"
  app_wheel=$1
  case "$extras" in
    core) ;;
    oci) pip_extra="oci" ;;
    oracle) pip_extra="oracle" ;;
    all) pip_extra="oci,oracle" ;;
    *) fail "Unsupported bundle capabilities: $extras" ;;
  esac
  wheel_spec=$app_wheel
  if [[ -n "$pip_extra" ]]; then
    wheel_spec="${app_wheel}[${pip_extra}]"
  fi

  if [[ "$mode" == "offline" ]]; then
    "$RUNTIME_DIR/venv/bin/python" -m pip install \
      --require-virtualenv \
      --disable-pip-version-check \
      --no-index \
      --find-links "$BUNDLE_DIR/wheelhouse" \
      "$wheel_spec" || fail "Offline runtime installation failed; verify target compatibility"
  elif [[ "$mode" == "online" ]]; then
    "$RUNTIME_DIR/venv/bin/python" -m pip install \
      --require-virtualenv \
      --disable-pip-version-check \
      "$wheel_spec" || fail "Online runtime installation failed; verify network and proxy access"
  else
    fail "Unsupported bundle mode: $mode"
  fi
  : > "$marker"
}

check_config() {
  local config_path=$1
  [[ -f "$config_path" && -r "$config_path" ]] || fail "Configuration is missing or unreadable: $config_path"
  if grep -Eq '\[REPLACE_[^]]+\]' "$config_path"; then
    fail "Configuration still contains [REPLACE_...] placeholders: $config_path"
  fi
}

doctor() {
  local config_path=$DEFAULT_CONFIG
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config)
        [[ $# -ge 2 && $2 != --* ]] || fail "--config requires a value"
        config_path=$2
        shift 2
        ;;
      *) fail "Unknown doctor option: $1" ;;
    esac
  done
  verify_bundle
  check_config "$config_path"
  ensure_runtime
  mkdir -p "$BUNDLE_DIR/out"
  "$RUNTIME_DIR/venv/bin/collector" run \
    --config "$config_path" \
    --out "$BUNDLE_DIR/out" \
    --dry-run
  printf 'Doctor: READY\n'
}

run_collector() {
  local config_path=$DEFAULT_CONFIG
  local has_config=false
  local has_out=false
  local expect_config=false
  local arg
  local run_args=()

  for arg in "$@"; do
    if [[ "$expect_config" == true ]]; then
      config_path=$arg
      expect_config=false
      continue
    fi
    case "$arg" in
      --config) has_config=true; expect_config=true ;;
      --out) has_out=true ;;
    esac
  done
  [[ "$expect_config" != true ]] || fail "--config requires a value"

  verify_bundle
  check_config "$config_path"
  ensure_runtime
  run_args=(run)
  if [[ "$has_config" != true ]]; then
    run_args+=(--config "$config_path")
  fi
  if [[ "$has_out" != true ]]; then
    run_args+=(--out "$BUNDLE_DIR/out")
  fi
  run_args+=("$@")
  exec "$RUNTIME_DIR/venv/bin/collector" "${run_args[@]}"
}

COMMAND=${1:-help}
if [[ $# -gt 0 ]]; then
  shift
fi
case "$COMMAND" in
  help|--help|-h) usage ;;
  list-profiles) [[ $# -eq 0 ]] || fail "list-profiles accepts no options"; list_profiles ;;
  init) init_config "$@" ;;
  verify) [[ $# -eq 0 ]] || fail "verify accepts no options"; verify_bundle; printf 'Integrity: OK\n' ;;
  doctor) doctor "$@" ;;
  run) run_collector "$@" ;;
  version)
    [[ $# -eq 0 ]] || fail "version accepts no options"
    printf 'oracle-compliance-collector %s (%s, %s)\n' \
      "$(metadata_value version)" "$(metadata_value mode)" "$(metadata_value extras)"
    ;;
  *) fail "Unknown command: $COMMAND" ;;
esac
