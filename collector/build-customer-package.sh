#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH=${BASH_SOURCE[0]}
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE=${SCRIPT_PATH%/*} ;;
  *) SCRIPT_BASE=. ;;
esac
readonly SOURCE_DIR=$(CDPATH= cd -- "$SCRIPT_BASE" && pwd -P)

usage() {
  cat <<'EOF'
Usage: build-customer-package.sh [OPTIONS]

Build a customer-ready Oracle compliance collector archive.

Options:
  --output PATH                    Output .tar.gz path
  --mode online|offline            Dependency delivery mode (default: online)
  --extras core|oci|oracle|all     Runtime capabilities (default: all)
  --python PATH                    Python 3.9+ used to build (default: python3)
  --force                          Replace an existing output archive
  --help                           Show this help and exit

Online bundles resolve third-party dependencies during first execution.
Offline bundles include wheels for the builder's current OS, architecture,
and Python compatibility. Build offline bundles on the customer's target.
EOF
}

fail() {
  printf 'build-customer-package.sh: %s\n' "$1" >&2
  exit 2
}

require_value() {
  local option=$1
  if [[ $# -lt 2 || $2 == --* ]]; then
    fail "$option requires a value"
  fi
}

OUTPUT_PATH=""
MODE="online"
EXTRAS="all"
PYTHON_BIN="python3"
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      require_value "$@"
      OUTPUT_PATH=$2
      shift 2
      ;;
    --mode)
      require_value "$@"
      MODE=$2
      shift 2
      ;;
    --extras)
      require_value "$@"
      EXTRAS=$2
      shift 2
      ;;
    --python)
      require_value "$@"
      PYTHON_BIN=$2
      shift 2
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --help)
      usage
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

case "$MODE" in
  online|offline) ;;
  *) fail "Unsupported mode: $MODE" ;;
esac

case "$EXTRAS" in
  core|oci|oracle|all) ;;
  *) fail "Unsupported extras selection: $EXTRAS" ;;
esac

if [[ "$PYTHON_BIN" == */* ]]; then
  [[ -f "$PYTHON_BIN" && -x "$PYTHON_BIN" ]] || fail "Python executable is not usable: $PYTHON_BIN"
else
  RESOLVED_PYTHON=$(command -v "$PYTHON_BIN" 2>/dev/null || true)
  [[ -n "$RESOLVED_PYTHON" ]] || fail "Python executable was not found: $PYTHON_BIN"
  PYTHON_BIN=$RESOLVED_PYTHON
fi

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
  || fail "Python 3.9 or newer is required"

VERSION=$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$SOURCE_DIR/pyproject.toml" | head -n 1)
[[ -n "$VERSION" ]] || fail "Unable to determine package version"

if [[ -z "$OUTPUT_PATH" ]]; then
  OUTPUT_PATH="./oracle-compliance-collector-${VERSION}-${MODE}-${EXTRAS}.tar.gz"
fi
case "$OUTPUT_PATH" in
  *.tar.gz) ;;
  *) fail "Output path must end in .tar.gz" ;;
esac

OUTPUT_PARENT=${OUTPUT_PATH%/*}
if [[ "$OUTPUT_PARENT" == "$OUTPUT_PATH" ]]; then
  OUTPUT_PARENT=.
fi
mkdir -p "$OUTPUT_PARENT"
OUTPUT_PARENT=$(CDPATH= cd -- "$OUTPUT_PARENT" && pwd -P)
OUTPUT_PATH="$OUTPUT_PARENT/${OUTPUT_PATH##*/}"
if [[ -e "$OUTPUT_PATH" && "$FORCE" != true ]]; then
  fail "Output already exists (use --force): $OUTPUT_PATH"
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/oracle-collector-package.XXXXXX")
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT HUP INT TERM

BUNDLE_NAME="oracle-compliance-collector-${VERSION}"
BUNDLE_DIR="$WORK_DIR/$BUNDLE_NAME"
mkdir -p "$BUNDLE_DIR/wheelhouse" "$BUNDLE_DIR/profiles" "$BUNDLE_DIR/customer-config"

"$PYTHON_BIN" -m build --wheel --outdir "$WORK_DIR/dist" "$SOURCE_DIR"
set -- "$WORK_DIR"/dist/oracle_compliance_collector-*.whl
[[ $# -eq 1 && -f "$1" ]] || fail "Expected exactly one application wheel"
APP_WHEEL=$1

PIP_EXTRA=""
case "$EXTRAS" in
  oci) PIP_EXTRA="oci" ;;
  oracle) PIP_EXTRA="oracle" ;;
  all) PIP_EXTRA="oci,oracle" ;;
esac

if [[ "$MODE" == "offline" ]]; then
  WHEEL_SPEC=$APP_WHEEL
  if [[ -n "$PIP_EXTRA" ]]; then
    WHEEL_SPEC="${APP_WHEEL}[${PIP_EXTRA}]"
  fi
  "$PYTHON_BIN" -m pip download \
    --disable-pip-version-check \
    --only-binary=:all: \
    --dest "$BUNDLE_DIR/wheelhouse" \
    "$WHEEL_SPEC"
else
  cp "$APP_WHEEL" "$BUNDLE_DIR/wheelhouse/"
fi

cp "$SOURCE_DIR/package/collector.sh" "$BUNDLE_DIR/collector.sh"
cp "$SOURCE_DIR/package/QUICKSTART.md" "$BUNDLE_DIR/QUICKSTART.md"
cp "$SOURCE_DIR/package/CONFIGURATION.md" "$BUNDLE_DIR/CONFIGURATION.md"
cp -R "$SOURCE_DIR/configs/hybrid" "$BUNDLE_DIR/profiles/"
cp -R "$SOURCE_DIR/configs/oci" "$BUNDLE_DIR/profiles/"
cp -R "$SOURCE_DIR/configs/onprem" "$BUNDLE_DIR/profiles/"
chmod 0755 "$BUNDLE_DIR/collector.sh"
chmod 0700 "$BUNDLE_DIR/customer-config"

{
  printf 'version=%s\n' "$VERSION"
  printf 'mode=%s\n' "$MODE"
  printf 'extras=%s\n' "$EXTRAS"
  printf 'python_min=3.9\n'
  printf 'build_os=%s\n' "$(uname -s)"
  printf 'build_arch=%s\n' "$(uname -m)"
} > "$BUNDLE_DIR/BUNDLE-METADATA"

(
  cd "$BUNDLE_DIR"
  find . -type f ! -name SHA256SUMS ! -path './customer-config/*' -print | LC_ALL=C sort |
    while IFS= read -r file; do
      clean_file=${file#./}
      if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$clean_file"
      elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$clean_file"
      else
        fail "sha256sum or shasum is required"
      fi
    done > SHA256SUMS
)

if [[ -e "$OUTPUT_PATH" ]]; then
  rm -f "$OUTPUT_PATH"
fi
COPYFILE_DISABLE=1 tar -czf "$OUTPUT_PATH" -C "$WORK_DIR" "$BUNDLE_NAME"

printf 'Customer package created: %s\n' "$OUTPUT_PATH"
printf 'Mode: %s; capabilities: %s; profiles: 19\n' "$MODE" "$EXTRAS"
