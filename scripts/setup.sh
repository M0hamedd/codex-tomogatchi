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

if command -v python3 >/dev/null 2>&1; then
  PYTHON=(python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON=(python)
else
  echo "Python 3 was not found." >&2
  exit 1
fi

echo "Codex Tomogatchi setup"
echo "Repo: $REPO_ROOT"

cd "$REPO_ROOT"

if [[ "$SKIP_NPM_INSTALL" -eq 0 ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm was not found. Install Node.js LTS and rerun setup." >&2
    exit 1
  fi
  npm install
fi

"${PYTHON[@]}" "$PLUGIN_SCRIPT" settings --init
"${PYTHON[@]}" "$PLUGIN_SCRIPT" install

if [[ "$SKIP_RESET" -eq 0 ]]; then
  "${PYTHON[@]}" "$PLUGIN_SCRIPT" reset --confirm --from-now
fi

if [[ "$SKIP_MARKETPLACE" -eq 0 ]] && command -v codex >/dev/null 2>&1; then
  codex plugin marketplace add "$REPO_ROOT" || true
fi

if [[ "$SKIP_LAUNCH" -eq 0 ]]; then
  npm start >/dev/null 2>&1 &
fi

echo "Setup complete."
"${PYTHON[@]}" "$PLUGIN_SCRIPT" settings
