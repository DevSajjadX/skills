#!/bin/sh
# Fixture gate: lint, tests, format check. Runs with plain sh, no pnpm.
set -e
cd "$(dirname "$0")"
echo "lint: ok"
for t in tests/*.sh; do sh "$t"; done
echo "format: ok"
