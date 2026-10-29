#!/usr/bin/env bash
# Dry run of /wrap step 2 (review snapshot), step 7 (Squash) and step 7b (Merge) against a throwaway repo with a bare "remote".
# Replays the skill's exact git commands for the local scope and the --f scope,
# then provokes each guard. Prints PASS/FAIL per assertion; exit 1 on any FAIL.
# The replay is a hand copy: the parity block at the end fails when SKILL.md rewords a replayed command.
set -u
SKILL="$(cd "$(dirname "$0")/.." && pwd)/SKILL.md"

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/wrap-dry-run.XXXXXX") && [ -d "$ROOT" ] || exit 1
trap 'rm -rf "$ROOT"' EXIT
REMOTE_DIR="$ROOT/remote.git"
WORK="$ROOT/work"
OTHER="$ROOT/other"
FAILS=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAILS=$((FAILS + 1)); }
check() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

commit() { # commit <file> <content> <message>
  mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" >"$1"; git add "$1"; git commit -q -m "$3"
}

# --- fixture: remote named "fork" (not origin), default branch main, one base commit
git init -q --bare -b main "$REMOTE_DIR"
git init -q -b main "$WORK"; cd "$WORK" || exit 1
git config user.email t@t; git config user.name t
commit README.md "base" "chore: base"
printf '#!/bin/sh\n# fake typecheck: ui must not reference an api symbol the api layer lacks\nif grep -q useBand ui/*.ts 2>/dev/null && ! grep -q "export const band" api/*.ts 2>/dev/null; then echo "typecheck failed"; exit 1; fi\nexit 0\n' >check.sh
chmod +x check.sh; git add check.sh; git commit -q -m "chore: fake typecheck"
git remote add fork "$REMOTE_DIR"; git push -q -u fork main
git remote set-head fork main

# --- work branch: 5 per-task commits across 3 concerns; first 3 pushed, last 2 local
git checkout -q -b feat/x
commit api/band.ts   "export const band = 1;"    "wip: api band"
commit ui/chip.ts    "import {band} from '../api/band'; useBand(band);" "wip: chip uses band"
commit docs/notes.md "band"                       "wip: doc band"
git push -q -u fork feat/x
commit api/band.ts   "export const band = 2;"    "wip: api band v2"
commit ui/chip.ts    "import {band} from '../api/band'; useBand(band); // v2" "wip: chip v2"

# =============================== pre-checks (skill text) ===============================
# step 2's refs; R and DEF are globals the helpers read
remote_name() { # the upstream's remote, else the sole remote
  local up; up=$(git rev-parse --abbrev-ref @{u} 2>/dev/null)
  if [ -n "$up" ]; then echo "${up%%/*}"; elif [ "$(git remote | wc -l)" -eq 1 ]; then git remote; fi
}
def_for() { # remote HEAD ref, else the remote's own HEAD, else the one of main/master that exists; fails = stop and ask
  local d b n=0
  d=$(git symbolic-ref --short "refs/remotes/$R/HEAD" 2>/dev/null); d=${d#"$R/"}
  [ -z "$d" ] && [ -n "$R" ] && d=$(git ls-remote --symref "$R" HEAD 2>/dev/null | awk '$1 == "ref:" && $3 == "HEAD" { sub("^refs/heads/", "", $2); print $2 }')
  if [ -z "$d" ]; then
    for b in main master; do git rev-parse -q --verify "refs/heads/$b" >/dev/null && { d=$b; n=$((n + 1)); }; done
    [ $n = 1 ] || return 1
  fi
  echo "$d"
}
remote_for() { git rev-parse -q --verify @{u} || git rev-parse -q --verify "refs/remotes/$R/$(git branch --show-current)"; }
base_for() { # merge-base with whichever of DEF and R/DEF exist
  local r refs=(); for r in "refs/heads/$DEF" "refs/remotes/$R/$DEF"; do git rev-parse -q --verify "$r" >/dev/null && refs+=("$r"); done
  git merge-base HEAD "${refs[@]}"
}
scope_for() { # --f: BASE, refused on DEF (prints nothing, fails); else the parent of the oldest commit no remote has
  local on_def=0 u; [ "$(git branch --show-current)" = "$DEF" ] && on_def=1
  if [ "${1:-}" = --f ]; then [ $on_def = 0 ] && base_for; return; fi
  if [ $on_def = 0 ] && git rev-parse -q --verify "refs/heads/$DEF" >/dev/null; then u=$(git rev-list HEAD --not --remotes "$DEF" | tail -1)
  else u=$(git rev-list HEAD --not --remotes | tail -1); fi
  [ -n "$u" ] && git rev-parse -q --verify "$u^" || git rev-parse HEAD
}
prechecks() { # step 7's pre-checks bar --f on DEF (scope_for refuses that) -> fails = stop
  local remote; git symbolic-ref -q HEAD >/dev/null || return 1
  remote=$(remote_for)
  [ -z "$remote" ] || git merge-base --is-ancestor "$remote" HEAD || return 1
  [ -z "$(git rev-list --merges "$(base_for)"..HEAD)" ]
}
R=$(remote_name); DEF=$(def_for); REMOTE=$(remote_for); BASE=$(base_for)
check "remote derived from upstream (=fork, not origin)" '[ "$R" = fork ]'
check "default branch detected from remote HEAD"          '[ "$DEF" = main ]'
check "upstream is an ancestor of HEAD"                   'git merge-base --is-ancestor "$REMOTE" HEAD'
check "no merge commits in BASE..HEAD"                    '[ -z "$(git rev-list --merges "$BASE"..HEAD)" ]'
check "step 7 pre-checks pass on the work branch"         'prechecks'
SCOPE=$(scope_for)
check "default scope = the upstream, an ancestor of HEAD" '[ "$SCOPE" = "$REMOTE" ]'

# =============================== step 2: review snapshot ($TREE) =======================
printf 'x\n' >>docs/notes.md; echo junk >untracked.tmp; echo ign >ignored.log; printf '*.log\n' >.gitignore
TREE=$(GIT_INDEX_FILE=$(mktemp -u) sh -c 'git read-tree HEAD && git add -A && git write-tree; rm -f "$GIT_INDEX_FILE"')
check "snapshot: a tree object, not a commit"              '[ "$(git cat-file -t "$TREE")" = tree ]'
check "snapshot: uncommitted tracked edit included"        'git diff "$SCOPE" "$TREE" -- docs/notes.md | grep -q "^+x$"'
check "snapshot: untracked file included"                  'git grep -q junk "$TREE" -- untracked.tmp'
check "snapshot: ignored file excluded"                    '! git grep -q ign "$TREE" -- ignored.log 2>/dev/null'
check "snapshot: local commits above SCOPE included"       'git diff "$SCOPE" "$TREE" -- api/band.ts | grep -q "band = 2"'
check "snapshot: real index and working tree untouched"    'git diff --cached --quiet && [ "$(git status --porcelain | wc -l | tr -d " ")" = 3 ]'
git checkout -q docs/notes.md; rm -f untracked.tmp ignored.log .gitignore

# =============================== local scope (no --f) ===================================
park() { # Method 1 without `c`: tracked only; PARKED only when the stash ref moved
  local s0; s0=$(git rev-parse -q --verify refs/stash); git stash push -q
  PARKED=; [ "$(git rev-parse -q --verify refs/stash)" != "$s0" ] && PARKED=1
}
unpark() { if [ -n "$PARKED" ]; then git stash pop -q; fi; PARKED=; }
printf 'users-old-wip\n' >>README.md; git stash push -q -m user-wip   # the user's own stash, not wrap's
printf 'x\n' >>docs/notes.md                       # an uncommitted wrap edit, tracked file
echo junk >untracked.tmp                           # untracked: must survive, never stashed
park
OLD=$(git rev-parse HEAD)
git reset -q --soft "$REMOTE" && git reset -q
git add api/band.ts;  git commit -q -m "feat(api): band v2"
git add ui/chip.ts;   git commit -q -m "feat(ui): chip follows band v2"
check "local regroup: 2 wip commits -> 2 concern commits" '[ "$(git rev-list --count "$REMOTE"..HEAD)" = 2 ]'
check "local regroup: content identical to OLD"           'git diff --quiet "$OLD" HEAD'
check "local regroup: pushed commits untouched"           '[ "$(git rev-parse "$REMOTE")" = "$(git rev-parse fork/feat/x)" ]'
unpark
check "wrap edit restored from stash"                     'grep -q x docs/notes.md'
check "untracked file untouched by tracked-only stash"    '[ -f untracked.tmp ]'
git checkout -q docs/notes.md; rm untracked.tmp
# a clean tree parks nothing, so nothing may be popped: a blind pop applies the user's own stash
park; OLD=$(git rev-parse HEAD)
git reset -q --soft "$REMOTE" && git reset -q; git add api/band.ts ui/chip.ts; git commit -q -m "feat: band v2"
unpark
check "clean tree: the user's stash is not applied"       'git diff --quiet && ! grep -q users-old-wip README.md'
check "clean tree: the user's stash is still listed"      'git stash list | grep -q user-wip'
git reset -q --hard "$OLD"

# =============================== --f scope (whole branch + lease) ======================
printf 'x\n' >>docs/notes.md                       # a wrap edit on a file the regroup reshapes
park
check "--f scope on a side branch = BASE"           '[ "$(scope_for --f)" = "$BASE" ]'
OLD=$(git rev-parse HEAD)
git reset -q --soft "$BASE" && git reset -q
git add api/band.ts;   git commit -q -m "feat(api): band"
git add ui/chip.ts;    git commit -q -m "feat(ui): chip uses band"
git add docs/notes.md; git commit -q -m "docs: band"
check "--f regroup: 5 wip -> 3 concern commits"      '[ "$(git rev-list --count "$BASE"..HEAD)" = 3 ]'
check "--f regroup: content identical to OLD"        'git diff --quiet "$OLD" HEAD'
ok=1; for sha in $(git rev-list --reverse "$BASE"..HEAD); do git checkout -q "$sha" && ./check.sh >/dev/null || ok=0; done; git checkout -q feat/x
check "--f: every intermediate commit passes typecheck (api before ui)" '[ $ok = 1 ]'
git push -q --force-with-lease=feat/x:"$REMOTE" "$R" feat/x
check "--f: force-with-lease accepted, remote now at HEAD" '[ "$(git rev-parse fork/feat/x)" = "$(git rev-parse HEAD)" ]'
unpark                                              # after step 6
check "--f: wrap edit back after step 6"             'grep -q x docs/notes.md'
git checkout -q docs/notes.md

# =============================== guards ==================================================
# 1) wrong order breaks bisectability: ui before api must fail the per-commit check -> reset --hard OLD
printf 'x\n' >>docs/notes.md; park; OLD=$(git rev-parse HEAD)
git reset -q --soft "$BASE" && git reset -q
git add ui/chip.ts;    git commit -q -m "feat(ui): chip uses band"
git add api/band.ts;   git commit -q -m "feat(api): band"
git add docs/notes.md; git commit -q -m "docs: band"
ok=1; for sha in $(git rev-list --reverse "$BASE"..HEAD); do git checkout -q "$sha" && ./check.sh >/dev/null || ok=0; done; git checkout -q feat/x
check "guard: ui-before-api ordering is caught by the per-commit typecheck" '[ $ok = 0 ]'
git reset -q --hard "$OLD"; unpark                # abort: pop
check "guard: the parked wrap edit survives the reset --hard OLD" 'grep -q x docs/notes.md'
git checkout -q docs/notes.md

# 2) parity failure -> reset --hard OLD
OLD=$(git rev-parse HEAD)
git reset -q --soft "$BASE" && git reset -q
git add api/band.ts ui/chip.ts; git commit -q -m "feat: partial (docs forgotten)"
git diff --quiet "$OLD" HEAD && parity=1 || parity=0
[ $parity = 0 ] && git reset -q --hard "$OLD"
check "guard: forgotten file -> parity fails -> reset --hard OLD restores" '[ $parity = 0 ] && git diff --quiet "$OLD" HEAD && [ "$(git rev-parse HEAD)" = "$OLD" ]'
git checkout -q -- .

# 3) stale lease: another clone pushes first -> our lease must be rejected
git clone -q "$REMOTE_DIR" "$OTHER"; ( cd "$OTHER" && git config user.email o@o && git config user.name o && git checkout -q feat/x && echo other >other.md && git add other.md && git commit -q -m "wip: someone else" && git push -q origin feat/x )
cd "$WORK" || exit 1; LEASE=$(git rev-parse fork/feat/x)   # what we last saw
git commit -q --allow-empty -m "chore: local only"
git push -q --force-with-lease=feat/x:"$LEASE" "$R" feat/x 2>/dev/null && pushed=1 || pushed=0
check "guard: lease rejected when remote moved underneath us" '[ $pushed = 0 ]'
git fetch -q "$R"
check "guard: after fetch, REMOTE not ancestor of HEAD -> skill must stop" '! prechecks'
git reset -q --hard "$R/feat/x"

# 4) merge commit in range -> stop
git checkout -q main; commit README.md "main moved" "chore: main moved"; git push -q "$R" main
git checkout -q feat/x; git merge -q --no-edit main >/dev/null
check "guard: merge commit in BASE..HEAD -> stop"   '! prechecks'

# 5) default branch: plain `s` regroups only unpushed commits, `--f` is refused
git checkout -q main
commit docs/a.md "a" "wip: a"; commit docs/b.md "b" "wip: b"; commit docs/a.md "a v2" "wip: a v2"
PUSHED=$(git rev-parse "$R/$DEF"); OLD=$(git rev-parse HEAD)
F=$(scope_for --f) && { git reset -q --soft "$F" && git reset -q; }
check "guard: --f on default branch -> refused, nothing rewritten" '[ -z "$F" ] && [ "$(git rev-parse HEAD)" = "$OLD" ]'
SCOPE=$(scope_for)
check "default branch, plain s: scope is the upstream, not HEAD"  '[ "$SCOPE" = "$PUSHED" ]'
git reset -q --soft "$SCOPE" && git reset -q
git add docs/a.md; git commit -q -m "docs: a"
git add docs/b.md; git commit -q -m "docs: b"
check "default branch, plain s: 3 wip -> 2 concern commits"       '[ "$(git rev-list --count "$PUSHED"..HEAD)" = 2 ]'
check "default branch, plain s: content identical to OLD"         'git diff --quiet "$OLD" HEAD'
check "default branch, plain s: pushed commits keep their hashes" '[ "$(git rev-parse HEAD~2)" = "$PUSHED" ] && [ "$(git rev-parse "$R/$DEF")" = "$PUSHED" ]'
git branch -q --unset-upstream
check "default branch, no upstream: scope still stops at the pushed commit" '[ "$(scope_for)" = "$PUSHED" ]'
git branch -q -u "$R/$DEF"; git reset -q --hard "$PUSHED"
git checkout -q --detach
check "guard: detached HEAD -> refuse" '! prechecks'

# =============================== step 7b: merge (`m`) ====================================
# Replays the skill's merge method: pre-checks, sync target, ff-or-merge-commit, gate, delete branch.
merge_step() { # merge_step <feature> <target> <gate cmd> -> sets MERGED (1/0), TARGET_OLD, FEATURE_SHA, FEATURE_UP
  local target=$2 tu; MERGED=0
  git rev-parse --verify -q "refs/heads/$target" >/dev/null || return 1
  [ "$(git rev-parse --abbrev-ref HEAD)" != "$target" ] || return 1
  tu=$(git rev-parse --abbrev-ref "$target@{u}" 2>/dev/null)
  if [ -n "$tu" ]; then git fetch -q "${tu%%/*}"; git merge-base --is-ancestor "$target" "$tu" || return 1; fi
  [ -z "$(git status --porcelain --untracked-files=no)" ] || return 1
  FEATURE_UP=$(git rev-parse --abbrev-ref "$1@{u}" 2>/dev/null)
  git checkout -q "$target"; [ -n "$tu" ] && git merge -q --ff-only "@{u}"
  TARGET_OLD=$(git rev-parse HEAD)
  git merge -q --ff-only "$1" 2>/dev/null || git merge -q --no-ff --no-edit "$1"
  if $3 >/dev/null; then FEATURE_SHA=$(git rev-parse "$1"); git merge-base --is-ancestor "$1" HEAD && git branch -q -D "$1" || return 1; MERGED=1
  else git reset -q --hard "$TARGET_OLD"; git checkout -q "$1"; MERGED=0; fi
}

# 1) happy path: regroup, then fast-forward into the default branch
git checkout -q main; git checkout -q -b feat/m1
commit docs/m1.md "m1" "wip: m1"; commit docs/m1.md "m1 v2" "wip: m1 v2"
OLD=$(git rev-parse HEAD); git reset -q --soft "$(scope_for)" && git reset -q
git add docs/m1.md; git commit -q -m "docs: m1"
check "m: regroup parity before merge" 'git diff --quiet "$OLD" HEAD'
merge_step feat/m1 "$DEF" ./check.sh
check "m: merged and gate passed"                       '[ "${MERGED:-0}" = 1 ]'
check "m: fast-forward (target HEAD = feature sha)"     '[ "$(git rev-parse HEAD)" = "$FEATURE_SHA" ]'
check "m: now on target"                                '[ "$(git rev-parse --abbrev-ref HEAD)" = "$DEF" ]'
check "m: feature branch deleted"                       '! git rev-parse --verify -q refs/heads/feat/m1 >/dev/null'
check "m: tree identical to the feature tip"            'git diff --quiet "$FEATURE_SHA" HEAD'
check "m: restore line works (git branch <name> <sha>)" 'git branch feat/m1 "$FEATURE_SHA" && git branch -q -D feat/m1'
git push -q "$R" main

# 2) target moved (and is at its upstream) -> merge commit, never squash
git checkout -q -b feat/m2; commit docs/m2.md "m2" "feat: m2"
git checkout -q main; commit docs/main2.md "main2" "chore: main moved again"; git push -q "$R" main
git checkout -q feat/m2
merge_step feat/m2 "$DEF" ./check.sh
check "m: non-ff -> exactly one merge commit"           '[ "$(git rev-list --count --merges "$TARGET_OLD"..HEAD)" = 1 ]'
check "m: merge commit has the feature tip as parent"   'git rev-parse HEAD^2 | grep -q "$FEATURE_SHA"'
check "m: both sides present in the merged tree"        '[ -f docs/m2.md ] && [ -f docs/main2.md ]'
check "m: feature branch deleted after merge commit"    '! git rev-parse --verify -q refs/heads/feat/m2 >/dev/null'
git push -q "$R" main

# 3) gate fails on the merged result -> target back at TARGET_OLD, feature branch kept, back on it
git checkout -q -b feat/m3; commit ui/bad.ts "useBand(1);" "feat: bad ui"   # check.sh: useBand without api band
merge_step feat/m3 "$DEF" ./check.sh
check "m guard: gate failure -> not merged"             '[ "$MERGED" = 0 ]'
check "m guard: target reset to TARGET_OLD"             '[ "$(git rev-parse "$DEF")" = "$TARGET_OLD" ]'
check "m guard: feature branch still present"           'git rev-parse --verify -q refs/heads/feat/m3 >/dev/null'
check "m guard: back on the feature branch"             '[ "$(git rev-parse --abbrev-ref HEAD)" = feat/m3 ]'

# 4) `m` with only uncommitted work (a tracked edit and a new file), nothing committed above scope
git checkout -q main; git checkout -q -b feat/m4
printf 'm4\n' >>README.md; echo m4 >docs/m4.md
git add README.md docs/m4.md; git commit -q -m "feat: m4"   # step 7 with `c`: step 8's commit first, explicit paths
check "m, uncommitted only: the early commit sits above scope" '[ "$(git rev-list --count "$(scope_for)"..HEAD)" = 1 ]'
merge_step feat/m4 "$DEF" ./check.sh
check "m, uncommitted only: merged"                     '[ "$MERGED" = 1 ]'
check "m, uncommitted only: target has the edit and the new file" '[ "$(git branch --show-current)" = "$DEF" ] && grep -q m4 README.md && [ -f docs/m4.md ]'
git push -q "$R" main

# 5) a pushed feature with a commit above its upstream: `branch -d` asks the upstream, not target
git checkout -q -b feat/m5; commit docs/m5.md "m5" "feat: m5"; git push -q -u "$R" feat/m5
commit docs/m5.md "m5 v2" "feat: m5 v2"
merge_step feat/m5 "$DEF" ./check.sh
check "m, pushed feature: merged and the local branch deleted" '[ "$MERGED" = 1 ] && ! git rev-parse --verify -q refs/heads/feat/m5 >/dev/null'
check "m, pushed feature: target holds FEATURE_SHA"     'git merge-base --is-ancestor "$FEATURE_SHA" HEAD'
check "m, pushed feature: its upstream recorded for the report" '[ "$FEATURE_UP" = "$R/feat/m5" ]'
git push -q "$R" main

# 6) pre-checks: target ahead of its upstream, or current branch is the target -> refuse
git checkout -q main; git commit -q --allow-empty -m "chore: local-only on main"; git checkout -q feat/m3
check "m guard: target ahead of upstream -> refuse"     '! merge_step feat/m3 "$DEF" ./check.sh && [ "$(git rev-parse --abbrev-ref HEAD)" = feat/m3 ]'
git checkout -q main
check "m guard: on the target branch -> refuse"         '! merge_step main "$DEF" ./check.sh'

# =============================== scope: only commits no remote has ======================
# a) local DEF ahead of its remote (main holds "chore: local-only on main"); a feature cut from it
git checkout -q -b feat/ahead; commit docs/ahead.md "ahead" "wip: ahead"
check "local DEF ahead: BASE is local DEF"                         '[ "$(base_for)" = "$(git rev-parse main)" ]'
check "local DEF ahead: plain scope holds only the feature commit" '[ "$(git rev-list --count "$(scope_for)"..HEAD)" = 1 ]'
check "local DEF ahead: --f scope holds only the feature commit"   '[ "$(git rev-list --count "$(scope_for --f)"..HEAD)" = 1 ]'

# b) local DEF stale: another clone moved the remote's DEF on; a feature cut from the remote's DEF
( cd "$OTHER" && git checkout -q main && git pull -q && commit docs/other.md "o" "chore: other's main commit" && git push -q origin main )
git fetch -q "$R"; git checkout -q --no-track -b feat/stale "$R/$DEF"; commit docs/stale.md "s" "wip: stale"
check "stale local DEF: BASE is the remote's DEF"                  '[ "$(base_for)" = "$(git rev-parse "$R/$DEF")" ]'
check "stale local DEF: plain scope holds only the feature commit" '[ "$(git rev-list --count "$(scope_for)"..HEAD)" = 1 ]'
check "stale local DEF: --f scope holds only the feature commit"   '[ "$(git rev-list --count "$(scope_for --f)"..HEAD)" = 1 ]'

# c) pushed without -u: no upstream, yet the remote has the first commit
git checkout -q --no-track -b feat/nou "$R/$DEF"; commit docs/nou.md "1" "wip: nou 1"; git push -q "$R" feat/nou; commit docs/nou.md "2" "wip: nou 2"
check "pushed without -u: REMOTE is the same-name remote branch"   '[ "$(remote_for)" = "$(git rev-parse "$R/feat/nou")" ]'
check "pushed without -u: plain scope stops at the pushed commit"  '[ "$(scope_for)" = "$(git rev-parse "$R/feat/nou")" ]'

# d) a master repo: no remote, then a remote without refs/remotes/<r>/HEAD
LOCAL="$ROOT/local"; git init -q -b master "$LOCAL"; cd "$LOCAL" || exit 1; git config user.email t@t; git config user.name t
commit a.md "a" "chore: a"; commit a.md "b" "chore: b"
R=$(remote_name); DEF=$(def_for)
check "no remote: DEF is the one of main/master that exists"       '[ "$DEF" = master ]'
check "no remote, on DEF: scope is HEAD, step 7 skips"             '[ "$(scope_for)" = "$(git rev-parse HEAD)" ]'
git branch main
check "no remote, both main and master: DEF unresolved -> stop"    '! def_for >/dev/null'
git init -q --bare -b master "$ROOT/local.git"; git remote add up "$ROOT/local.git"; git push -q up master
R=$(remote_name)
check "no upstream: R is the sole remote"                          '[ "$R" = up ]'
check "no remote HEAD ref: DEF is the remote's own HEAD, not a guess" '[ "$(def_for)" = master ] && ! git rev-parse -q --verify refs/remotes/up/HEAD >/dev/null'
cd "$WORK" || exit 1

# =============================== step 8b: PR mode (`pr`) =================================
# Replays the method's refusals and the merge check with a fake host CLI on PATH that records calls.
BIN="$ROOT/bin"; CALLS="$ROOT/host-calls"; mkdir -p "$BIN"; : >"$CALLS"
cat >"$BIN/glab" <<'FAKE'
#!/bin/sh
echo "$*" >>"$FAKE_CALLS"
case "$*" in
  "mr view"*) echo "{\"sha\":\"$FAKE_PR_SHA\"}" ;;
esac
FAKE
chmod +x "$BIN/glab"
pr_step() { # pr_step <flow> <merge:0|1> -> sets PR_RESULT (refused-flow|refused-branch|open|refused-sha|merged)
  local flow=$1 merge=$2 head sha; PR_RESULT=
  [ "$flow" = direct ] && { PR_RESULT=refused-flow; return 1; }
  [ "$(git branch --show-current)" = "$DEF" ] && { PR_RESULT=refused-branch; return 1; } # pre-check: ask for a name, git switch -c, before any commit
  printf 'what changed\n' >"$ROOT/desc.md"
  git push -q -u "$R" HEAD 2>/dev/null; PATH="$BIN:$PATH" glab mr create --target-branch "$DEF" --title t --description-file "$ROOT/desc.md" --yes
  PR_RESULT=open; [ "$merge" = 1 ] || return 0
  head=$(git rev-parse HEAD); sha=$(PATH="$BIN:$PATH" glab mr view 7 -F json | sed 's/.*"sha":"\([^"]*\)".*/\1/')
  [ "$head" = "$sha" ] || { PR_RESULT=refused-sha; return 1; }
  PATH="$BIN:$PATH" glab mr merge 7 --sha "$head" --auto-merge=false --yes; PR_RESULT=merged
}
R=fork; DEF=main; export FAKE_CALLS="$CALLS"
git checkout -q main; : >"$CALLS"
pr_step pr 0
MAIN_TIP=$(git rev-parse main)
check "pr guard: on the default branch -> asks for a branch, no host call, no commit on main" '[ "$PR_RESULT" = refused-branch ] && [ ! -s "$CALLS" ] && [ "$(git rev-parse main)" = "$MAIN_TIP" ]'
git checkout -q -b feat/pr1; commit docs/pr1.md "pr1" "feat: pr1"
pr_step direct 0
check "pr guard: flow direct -> refused, use m, no host call"    '[ "$PR_RESULT" = refused-flow ] && [ ! -s "$CALLS" ]'
FAKE_PR_SHA=0000000000000000000000000000000000000000 pr_step pr 1
check "pr guard: PR head differs from HEAD -> merge refused"     '[ "$PR_RESULT" = refused-sha ] && ! grep -q "mr merge" "$CALLS"'
check "pr: the PR was still opened (reported as not shipped)"    'grep -q "mr create" "$CALLS"'
FAKE_PR_SHA=$(git rev-parse HEAD) pr_step pr 1
check "pr: head equals PR head -> merged through the host"       '[ "$PR_RESULT" = merged ] && grep -q "mr merge 7 --sha $(git rev-parse HEAD) --auto-merge=false --yes" "$CALLS"'
check "pr: feature branch pushed with -u and tracks it"          '[ "$(git rev-parse "$R/feat/pr1")" = "$(git rev-parse HEAD)" ] && [ "$(git rev-parse --abbrev-ref @{u})" = "$R/feat/pr1" ]'
: >"$CALLS"; FAKE_PR_SHA=x pr_step pr 0
check "pr without --m: opens only, never merges"                 '[ "$PR_RESULT" = open ] && ! grep -q "mr merge" "$CALLS"'

# 7b's flow pre-check, replayed against the flow parsed from a fixture Ship section
ship_flow() { sed -n 's/^- flow: *\([a-z]*\).*/\1/p' "$1" | head -1; } # empty = no explicit flow
m_pre() { [ "$(ship_flow "$1")" = pr ] && [ "$2" = "$DEF" ] && return 1; return 0; } # m_pre <AGENTS file> <target>
printf '# P\n## Ship\n- flow: pr\n' >"$ROOT/a-pr.md"; printf '# P\n## Ship\n- flow: direct\n' >"$ROOT/a-direct.md"; printf '# P\nno ship section\n' >"$ROOT/a-none.md"
check "m guard: explicit flow pr, target = default branch -> refused (use pr --m)" '! m_pre "$ROOT/a-pr.md" "$DEF"'
check "m: explicit flow pr, a non-default target is fine"                          'm_pre "$ROOT/a-pr.md" release'
check "m: no Ship section, default-branch target keeps its plain behaviour"        'm_pre "$ROOT/a-none.md" "$DEF"'
check "m: flow direct, default-branch target is allowed"                           'm_pre "$ROOT/a-direct.md" "$DEF"'
git checkout -q main; git checkout -q -b feat/dir; commit docs/dir.md "d" "feat: dir"
git checkout -q main; commit docs/dir-main.md "dm" "chore: main moved under feat/dir"
DIR_OLD=$(git rev-parse main); git merge -q --ff-only feat/dir 2>/dev/null && dff=1 || dff=0
check "flow direct: diverged feature -> --ff-only fails, no merge commit, target unchanged" '[ $dff = 0 ] && [ "$(git rev-parse main)" = "$DIR_OLD" ] && [ -z "$(git rev-list --merges "$DIR_OLD"..main)" ]'
git checkout -q feat/dir; git rebase -q main; git checkout -q main
git merge -q --ff-only feat/dir && dff=1 || dff=0
check "flow direct: after rebasing the feature onto target, --ff-only succeeds" '[ $dff = 1 ]'

# =============================== parity: each replayed command, as SKILL.md words it ======
# A FAIL here means SKILL.md changed a command: update the helper above that replays it, then this line.
while IFS= read -r c; do check "SKILL.md: $c" 'grep -qF -- "$c" "$SKILL"'; done <<'EOF'
git rev-parse --abbrev-ref @{u}
git symbolic-ref --short refs/remotes/$R/HEAD
git ls-remote --symref $R HEAD
REMOTE=$(git rev-parse @{u} 2>/dev/null)
refs/remotes/$R/<branch>
git merge-base HEAD $DEF $R/$DEF
U=$(git rev-list HEAD --not --remotes $DEF | tail -1)
SCOPE=$U^
GIT_INDEX_FILE=$(mktemp -u) sh -c 'git read-tree HEAD && git add -A && git write-tree; rm -f "$GIT_INDEX_FILE"'
git symbolic-ref -q HEAD
git rev-list --merges $BASE..HEAD
S0=$(git rev-parse -q --verify refs/stash)
git stash push -q
git reset --soft <scope> && git reset
git diff --quiet $OLD HEAD
git checkout <sha> && <typecheck command>
git push --force-with-lease=<branch>:$REMOTE $R <branch>
git rev-parse --verify refs/heads/<target>
git merge-base --is-ancestor <target> $TU
git status --porcelain --untracked-files=no
FEATURE_UP=$(git rev-parse --abbrev-ref $FEATURE@{u} 2>/dev/null)
git merge --ff-only $FEATURE
git merge --no-ff --no-edit $FEATURE
git reset --hard $TARGET_OLD && git checkout $FEATURE
git merge-base --is-ancestor $FEATURE HEAD && git branch -D $FEATURE
git rev-parse HEAD
git push -u $R HEAD
git push --force-with-lease $R HEAD
git fetch $R $DEF
git rebase $R/$DEF
git show :2:<path>
glab mr view <n> -F json
glab mr create --target-branch $DEF --title <t> --description-file <f> --yes
glab mr merge <n> --sha <sha> --auto-merge=false --yes
git rev-parse HEAD^{tree}
git merge --continue
EOF

printf '\n%s\n' "$([ $FAILS = 0 ] && echo 'ALL PASS' || echo "$FAILS FAILED")"
[ $FAILS = 0 ]
