#!/usr/bin/env bash
# task-summary's task-page-template.html mirrors the tokens, dark mode and base CSS of
# pr-summary's pr-page-template.html (separate installs, so a copy, not a shared file).
# Diffs that block (`:root {` through `a { color: inherit; }`); exit 1 on drift.
set -u
d="$(dirname "$0")/../skills"
block() { sed -n '/^  :root {/,/^  a { color: inherit; }/p' "$1"; }
pr="$d/pr-summary/pr-page-template.html"
task="$d/task-summary/task-page-template.html"
[ -s "$pr" ] && [ -s "$task" ] || { echo "FAIL  template missing"; exit 1; }
[ -n "$(block "$pr")" ] && [ -n "$(block "$task")" ] || { echo "FAIL  shared block anchors not found"; exit 1; }
if diff <(block "$pr") <(block "$task"); then echo "PASS  shared CSS block in parity"; else echo "FAIL  shared CSS block drifted (pr-summary < > task-summary)"; exit 1; fi
