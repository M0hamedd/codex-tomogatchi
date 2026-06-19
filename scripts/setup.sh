#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_SCRIPT="$REPO_ROOT/plugins/codex-tomogatchi/scripts/tomogatchi.py"

SKIP_NPM_INSTALL=0
SKIP_MARKETPLACE=0
SKIP_RESET=0
SKIP_LAUNCH=0

for arg in "$@"; do
  case "$arg" in
    --skip-npm-install) SKIP_NPM_INSTALL=1 ;;
    --skip-marketplace) SKIP_MARKETPLACE=1 ;;
    --skip-reset) SKIP_RESET=1 ;;
    --skip-launch) SKIP_LAUNCH=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

test_python3() {
  "$@" -c "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)" >/dev/null 2>&1
}

PYTHON_CMD=()
if [[ -n "${PYTHON:-}" ]] && test_python3 "$PYTHON"; then
  PYTHON_CMD=("$PYTHON")
elif command -v python >/dev/null 2>&1 && test_python3 python; then
  PYTHON_CMD=(python)
elif command -v python3 >/dev/null 2>&1 && test_python3 python3; then
  PYTHON_CMD=(python3)
else
  echo "Python 3 was not found. Install Python 3, or set PYTHON to a Python 3 executable." >&2
  exit 1
fi

check_node_tooling() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js was not found. Install Node.js 22+ with npm 10+ and rerun setup." >&2
    exit 1
  fi
  local node_major
  node_major="$(node -p "Number(process.versions.node.split('.')[0])")"
  if [[ "$node_major" -lt 22 ]]; then
    echo "Node.js 22+ is required. Found $(node --version). Upgrade Node.js and rerun setup." >&2
    exit 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm was not found. Install Node.js 22+ with npm 10+ and rerun setup." >&2
    exit 1
  fi
  local npm_major
  npm_major="$(npm --version | cut -d. -f1)"
  if [[ "$npm_major" -lt 10 ]]; then
    echo "npm 10+ is required. Found npm $(npm --version). Upgrade Node.js/npm and rerun setup." >&2
    exit 1
  fi
}

echo "Codex Tomogatchi setup"
echo "Repo: $REPO_ROOT"

cd "$REPO_ROOT"

if [[ "$SKIP_NPM_INSTALL" -eq 0 || "$SKIP_LAUNCH" -eq 0 ]]; then
  check_node_tooling
fi

if [[ "$SKIP_NPM_INSTALL" -eq 0 ]]; then
  npm install
fi

"${PYTHON_CMD[@]}" "$PLUGIN_SCRIPT" settings --init
"${PYTHON_CMD[@]}" "$PLUGIN_SCRIPT" install

if [[ "$SKIP_RESET" -eq 0 ]]; then
  "${PYTHON_CMD[@]}" "$PLUGIN_SCRIPT" reset --confirm --from-now
fi

if [[ "$SKIP_MARKETPLACE" -eq 0 ]] && command -v codex >/dev/null 2>&1; then
  codex plugin marketplace add "$REPO_ROOT" || true
fi

if [[ "$SKIP_LAUNCH" -eq 0 ]]; then
  npm start >/dev/null 2>&1 &
fi

echo
echo "Setup complete. Running doctor..."
"${PYTHON_CMD[@]}" "$PLUGIN_SCRIPT" doctor
echo
if [[ "$SKIP_LAUNCH" -eq 0 ]]; then
  echo "Next: look for the Codex Tomogatchi overlay or tray icon."
else
  echo "Next: run npm start from this repo to launch the overlay."
fi
