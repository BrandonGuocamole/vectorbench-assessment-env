#!/usr/bin/env bash

echo "Starting VectorBench test watcher..."
echo "$(date): Test watcher started" > .vb_log

# Change to the repository root directory
cd "$(dirname "$0")/.." || exit

while true; do
  echo "Watching for changes in Python files..."
  find . -name '*.py' | entr -d bash -c "echo '$(date): Running tests' >> .vb_log && pytest -q >> .vb_log 2>&1"
  sleep 1
done 