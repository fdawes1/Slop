#!/usr/bin/env bash
# Run with the local venv, falling back to system python3
VENV="$(dirname "$0")/../venv/bin/python"
if [ -x "$VENV" ]; then
  exec "$VENV" "$(dirname "$0")/app.py" "$@"
else
  exec python3 "$(dirname "$0")/app.py" "$@"
fi
