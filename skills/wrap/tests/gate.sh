#!/usr/bin/env bash
# Self-test of hooks/wrap-gate.sh: feeds synthetic hook JSON on stdin and asserts the decision.
# Covers the `git commit` match (global opts, quotes, sh -c, prefixes and assignments, paths,
# near-misses, non-Bash tools), deny-once arming, UserPromptSubmit arm/disarm, PostToolUse
# Skill(wrap) arming, and the error when jq is missing.
# Prints PASS/FAIL per assertion; exit 1 on any FAIL.
set -u

HOOK="$(dirname "$0")/../hooks/wrap-gate.sh"
SESSION=gate-test-$$
MARK="${TMPDIR:-/tmp}/claude-wrap-armed-$SESSION"
trap 'rm -f "$MARK"' EXIT
FAILS=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAILS=$((FAILS + 1)); }
check()  { if eval "$2"; then pass "$1"; else fail "$1"; fi; }
expect() { if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (want $2, got $3)"; fi; }

run() { # run <event> <tool_name> <field> <value> -> permissionDecision, or "pass" when the hook printed nothing
  local out
  out=$(jq -n --arg e "$1" --arg t "$2" --arg f "$3" --arg v "$4" --arg s "$SESSION" \
    '{hook_event_name:$e, session_id:$s, tool_name:$t}
     + (if $f == "prompt" then {prompt:$v} else {tool_input:{($f):$v}} end)' | "$HOOK")
  if [ -z "$out" ]; then echo pass; else jq -r '.hookSpecificOutput.permissionDecision // "pass"' <<<"$out"; fi
}
bash_cmd() { run PreToolUse Bash command "$1"; }

# --- deny once, then pass
rm -f "$MARK"
expect "plain git commit, unarmed -> deny"         deny "$(bash_cmd 'git commit -m x')"
check  "deny arms the gate (marker exists)"        '[ -e "$MARK" ]'
expect "same command, armed -> pass"               pass "$(bash_cmd 'git commit -m x')"

# --- global options before the subcommand
rm -f "$MARK"; expect "git -C dir commit -> deny"        deny "$(bash_cmd 'git -C dir commit')"
rm -f "$MARK"; expect "git -c k=v commit -q -> deny"     deny "$(bash_cmd 'git -c k=v commit -q')"

# --- quotes are part of the text, never stripped
rm -f "$MARK"; expect "unbalanced quote in -m -> deny"   deny "$(bash_cmd "git commit -m \"it's\"")"
rm -f "$MARK"; expect "sh -c 'git commit' -> deny"       deny "$(bash_cmd "sh -c 'git commit -m x'")"

# --- near-misses
rm -f "$MARK"; expect "git commitment -> pass"           pass "$(bash_cmd 'git commitment')"
rm -f "$MARK"; expect "my-git commit -> pass"            pass "$(bash_cmd 'my-git commit')"
rm -f "$MARK"; expect "git log -> pass"                  pass "$(bash_cmd 'git log')"
rm -f "$MARK"; expect "Read tool with 'git commit' path -> pass" pass "$(run PreToolUse Read file_path 'git commit')"

# --- command position: only a `git commit` that runs fires, not one mentioned in written text
rm -f "$MARK"; expect "heredoc plan listing 'git commit -m foo' -> pass" pass "$(bash_cmd $'cat > plan.md <<\'EOF\'\n# Plan\n- git commit -m foo\nEOF')"
rm -f "$MARK"; expect "heredoc then git commit on its own line -> deny" deny "$(bash_cmd $'cat > plan.md <<\'EOF\'\n- step\nEOF\ngit commit -m y')"
rm -f "$MARK"; expect "cd x && git commit -> deny"        deny "$(bash_cmd 'cd x && git commit -m y')"
rm -f "$MARK"; expect "printf > f newline git commit -> deny" deny "$(bash_cmd $'printf "a" > f\ngit commit -m y')"
rm -f "$MARK"; expect "echo \"git commit is great\" -> pass" pass "$(bash_cmd 'echo "git commit is great"')"
rm -f "$MARK"; expect "echo \"run HUSKY=0 git commit later\" -> pass" pass "$(bash_cmd 'echo "run HUSKY=0 git commit later"')"
rm -f "$MARK"; expect "echo \"Great! git commit next\" -> pass" pass "$(bash_cmd 'echo "Great! git commit next"')"
rm -f "$MARK"; expect "echo \"see bin/git commit docs\" -> pass" pass "$(bash_cmd 'echo "see bin/git commit docs"')"

# --- the invocation forms the matcher covers, whatever runs them
rm -f "$MARK"; expect "\$(git commit) substitution -> deny"  deny "$(bash_cmd 'x=$(git commit -m y)')"
rm -f "$MARK"; expect "backtick git commit -> deny"          deny "$(bash_cmd 'x=`git commit -m y`')"
rm -f "$MARK"; expect "if ...; then git commit -> deny"      deny "$(bash_cmd 'if true; then git commit -m y; fi')"
rm -f "$MARK"; expect "for ...; do git commit -> deny"       deny "$(bash_cmd 'for f in a; do git commit -m y; done')"
rm -f "$MARK"; expect "xargs git commit -> deny"             deny "$(bash_cmd 'xargs git commit -m y')"
rm -f "$MARK"; expect "sudo git commit -> deny"              deny "$(bash_cmd 'sudo git commit -m y')"
rm -f "$MARK"; expect "{ git commit; } group -> deny"        deny "$(bash_cmd '{ git commit -m y; }')"
rm -f "$MARK"; expect "HUSKY=0 git commit -> deny"           deny "$(bash_cmd 'HUSKY=0 git commit -m y')"
rm -f "$MARK"; expect "cd x && A=1 B=2 git commit -> deny"   deny "$(bash_cmd 'cd x && A=1 B=2 git commit -m y')"
rm -f "$MARK"; expect "env FOO=1 git commit -> deny"         deny "$(bash_cmd 'env FOO=1 git commit -m y')"
rm -f "$MARK"; expect "nice git commit -> deny"              deny "$(bash_cmd 'nice git commit -m y')"
rm -f "$MARK"; expect "timeout 60 git commit -> deny"        deny "$(bash_cmd 'timeout 60 git commit -m y')"
rm -f "$MARK"; expect "nice -n 5 git commit -> deny"        deny "$(bash_cmd 'nice -n 5 git commit -m y')"
rm -f "$MARK"; expect "timeout -s KILL 60 git commit -> deny" deny "$(bash_cmd 'timeout -s KILL 60 git commit -m y')"
rm -f "$MARK"; expect "timeout --foreground 60 git commit -> deny" deny "$(bash_cmd 'timeout --foreground 60 git commit -m y')"
rm -f "$MARK"; expect "! git commit -> deny"                 deny "$(bash_cmd '! git commit -m y')"
rm -f "$MARK"; expect "/usr/bin/git commit -> deny"          deny "$(bash_cmd '/usr/bin/git commit -m y')"
rm -f "$MARK"; expect "git -C \"/a b\" commit -> deny"        deny "$(bash_cmd 'git -C "/a b" commit -m y')"
rm -f "$MARK"; expect "git -C '/a b' commit -> deny"         deny "$(bash_cmd "git -C '/a b' commit -m y")"

# --- UserPromptSubmit: /wrap arms, anything else disarms
rm -f "$MARK"
run UserPromptSubmit "" prompt '/wrap c' >/dev/null
check  "prompt '/wrap c' arms"                     '[ -e "$MARK" ]'
expect "commit after /wrap prompt -> pass"         pass "$(bash_cmd 'git commit -m x')"
run UserPromptSubmit "" prompt 'hello' >/dev/null
check  "prompt 'hello' disarms"                    '[ ! -e "$MARK" ]'
expect "commit after plain prompt -> deny"         deny "$(bash_cmd 'git commit -m x')"

# --- PostToolUse: only Skill(wrap) arms
rm -f "$MARK"
run PostToolUse Skill skill wrap >/dev/null
check  "Skill(wrap) arms"                          '[ -e "$MARK" ]'
rm -f "$MARK"
run PostToolUse Skill skill other >/dev/null
check  "Skill(other) does not arm"                 '[ ! -e "$MARK" ]'

# --- jq missing: the gate cannot read its input, so it says so (non-blocking error) instead of passing in silence
err=$(PATH=/nonexistent /bin/bash "$HOOK" </dev/null 2>&1 >/dev/null); rc=$?
check  "jq missing -> exit 1 with a message on stderr" '[ $rc = 1 ] && [[ "$err" == *jq* ]]'

printf '\n%s\n' "$([ $FAILS = 0 ] && echo 'ALL PASS' || echo "$FAILS FAILED")"
[ $FAILS = 0 ]
