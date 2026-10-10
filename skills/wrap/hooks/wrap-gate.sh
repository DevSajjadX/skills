#!/usr/bin/env bash
# Claude Code hook: soft commit/push gate. The first direct `git commit` or `git push` in a turn is denied once,
# telling the model to route through Skill(wrap, c); that deny arms the gate, so a retry
# (or wrap's own commit) passes. Never blocks work; worst case one retry.
# Wire all three events in settings.json to this one script:
#   UserPromptSubmit          · new turn disarms; a user-typed `/wrap ...` arms
#   PostToolUse  (Skill)      · Skill(wrap) arms
#   PreToolUse   (Bash)       · `git commit` or `git push` unarmed: deny once and arm
# The match is textual and positional: `git commit` must sit where a command starts, meaning line
# start, after `;` `&` `|` `(` a backtick or `{`, or inside a `-c '…'` shell string, optionally behind
# prefix words (`then`/`do`/`xargs`/`sudo`/`env`/`nice [opts]`/`timeout [opts] N`/`!`) and `VAR=value` assignments,
# with `git` path-qualified or carrying global options (`-C "/a b"`). Prose that merely mentions it
# passes. A textual matcher cannot cover every shell form: `eval`, aliases and `VAR="a b" git commit`
# pass, the accepted ceiling of a soft gate. Self-test: tests/gate.sh.
set -u
command -v jq >/dev/null || { echo 'wrap-gate: jq not found, commit gate disabled' >&2; exit 1; }
INPUT=$(cat)
# Fast path: RE below can only match a command containing commit or push.
PRE='"hook_event_name"[[:space:]]*:[[:space:]]*"PreToolUse"'
[[ $INPUT =~ $PRE && $INPUT != *commit* && $INPUT != *push* ]] && exit 0
EVENT=$(jq -r '.hook_event_name // ""' <<<"$INPUT")
SESSION=$(jq -r '.session_id // "nosession"' <<<"$INPUT")
MARK="${TMPDIR:-/tmp}/claude-wrap-armed-$SESSION"

case "$EVENT" in
  UserPromptSubmit)
    PROMPT=$(jq -r '.prompt // ""' <<<"$INPUT")
    if [[ "$PROMPT" =~ ^[[:space:]]*/wrap([[:space:]]|$) ]]; then touch "$MARK"; else rm -f "$MARK"; fi
    ;;
  PostToolUse)
    [[ "$(jq -r '.tool_name // ""' <<<"$INPUT")" == Skill ]] || exit 0
    [[ "$(jq -r '.tool_input.skill // ""' <<<"$INPUT")" == wrap ]] && touch "$MARK"
    ;;
  PreToolUse)
    [[ "$(jq -r '.tool_name // ""' <<<"$INPUT")" == Bash ]] || exit 0
    CMD=$(jq -r '.tool_input.command // ""' <<<"$INPUT")
    # `[prefixes] [path/]git [global opts] commit|push`; a global opt may carry one argument, quoted or not (-C dir, -c k=v)
    OPT='([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*'
    RE='(^|[;&|(`{]|-c[[:space:]]+['"'"'"])[[:space:]]*([[:space:]]*(then|else|do|xargs|time|sudo|nohup|command|env|nice'"$OPT"'|!|timeout'"$OPT"'[[:space:]]+[^[:space:]]+|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*)[[:space:]]+)*([^[:space:]]*/)?git([[:space:]]+-[^[:space:]]+([[:space:]]+("[^"]*"|'"'"'[^'"'"']*'"'"'|[^-[:space:]][^[:space:]]*))?)*[[:space:]]+(commit|push)([[:space:]]|$)'
    grep -Eq "$RE" <<<"$CMD" || exit 0
    [[ -e "$MARK" ]] && exit 0
    touch "$MARK"
    jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",
      permissionDecisionReason:"Commit/push gate (soft, fires once per turn): commits and pushes go through /wrap. Do it yourself now: do NOT ask the user and do NOT stop: invoke the Skill tool with skill \"wrap\" and args \"c\" (or \"c --p\" to push); wrap sweeps, verifies, and commits for you. If the Skill tool is not available to you (e.g. you are a subagent), simply rerun this exact command; it now passes."}}'
    ;;
esac
exit 0
