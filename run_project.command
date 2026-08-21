#!/bin/zsh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
else
  echo "Project environment not found. Double-click setup_project.command first."
  exit 1
fi

MPLCONFIGDIR="$PROJECT_DIR/.matplotlib-cache" "$PYTHON_BIN" -m src.run_all --data-dir ../archive

echo ""
echo "Run complete. Open: $PROJECT_DIR/outputs/RESULTS_SUMMARY.md"
