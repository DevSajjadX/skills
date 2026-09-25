#!/usr/bin/env bash
# Dry run of /wrap step 2 (review snapshot), step 7 (Squash) and step 7b (Merge) against a throwaway repo with a bare "remote".
# Replays the skill's exact git commands for the local scope and the --f scope,
# then provokes each guard. Prints PASS/FAIL per assertion; exit 1 on any FAIL.
set -u

ROOT=$(mktemp -d -t wrap-dry-run)
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

# --- fixture: remote named "stylit" (not origin), default branch main, one base commit
git init -q --bare -b main "$REMOTE_DIR"
git init -q -b main "$WORK"; cd "$WORK"
git config user.email t@t; git config user.name t
commit README.md "base" "chore: base"
printf '#!/bin/sh\n# fake typecheck: ui must not reference an api symbol the api layer lacks\nif grep -q useBand ui/*.ts 2>/dev/null && ! grep -q "export const band" api/*.ts 2>/dev/null; then echo "typecheck failed"; exit 1; fi\nexit 0\n' >check.sh
chmod +x check.sh; git add check.sh; git commit -q -m "chore: fake typecheck"
git remote add stylit "$REMOTE_DIR"; git push -q -u stylit main
git remote set-head stylit main

# --- work branch: 5 per-task commits across 3 concerns; first 3 pushed, last 2 local
git checkout -q -b feat/x
commit api/band.ts   "export const band = 1;"    "wip: api band"
commit ui/chip.ts    "import {band} from '../api/band'; useBand(band);" "wip: chip uses band"
commit docs/notes.md "band"                       "wip: doc band"
git push -q -u stylit feat/x
commit api/band.ts   "export const band = 2;"    "wip: api band v2"
commit ui/chip.ts    "import {band} from '../api/band'; useBand(band); // v2" "wip: chip v2"

# =============================== pre-checks (skill text) ===============================
UP=$(git rev-parse --abbrev-ref @{u} 2>/dev/null); R=${UP%%/*}
DEF=$(git symbolic-ref --short "refs/remotes/$R/HEAD" 2>/dev/null); DEF=${DEF#"$R/"}; DEF=${DEF:-main}
REMOTE=$(git rev-parse @{u}); BASE=$(git merge-base HEAD "$DEF")
scope_for() { # step 2's SCOPE, first match; --f on DEF prints nothing and fails (step 7 refuses it)
  local on_def=0 up; [ "$(git rev-parse --abbrev-ref HEAD)" = "$DEF" ] && on_def=1
  up=$(git rev-parse @{u} 2>/dev/null)
  if [ "${1:-}" = --f ]; then [ $on_def = 0 ] && git merge-base HEAD "$DEF"
  elif [ -n "$up" ] && git merge-base --is-ancestor "$up" HEAD; then echo "$up"
  elif [ $on_def = 0 ]; then git merge-base HEAD "$DEF"
  else git rev-parse HEAD; fi
}
check "remote derived from upstream (=stylit, not origin)" '[ "$R" = stylit ]'
check "default branch detected from remote HEAD"          '[ "$DEF" = main ]'
check "upstream is an ancestor of HEAD"                   'git merge-base --is-ancestor "$REMOTE" HEAD'
check "no merge commits in BASE..HEAD"                    '[ -z "$(git rev-list --merges "$BASE"..HEAD)" ]'
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

# =============================== local scope (bare /wrap or `s`) =======================
printf 'x\n' >>docs/notes.md                       # an uncommitted wrap edit, tracked file
echo junk >untracked.tmp                           # untracked: must survive, never stashed
git stash push -q                                   # tracked only
OLD=$(git rev-parse HEAD)
git reset -q --soft "$REMOTE" && git reset -q
git add api/band.ts;  git commit -q -m "feat(api): band v2"
git add ui/chip.ts;   git commit -q -m "feat(ui): chip follows band v2"
check "local regroup: 2 wip commits -> 2 concern commits" '[ "$(git rev-list --count "$REMOTE"..HEAD)" = 2 ]'
check "local regroup: content identical to OLD"           'git diff --quiet "$OLD" HEAD'
check "local regroup: pushed commits untouched"           '[ "$(git rev-parse "$REMOTE")" = "$(git rev-parse stylit/feat/x)" ]'
git stash pop -q
check "wrap edit restored from stash"                     'grep -q x docs/notes.md'
check "untracked file untouched by tracked-only stash"    '[ -f untracked.tmp ]'
git checkout -q docs/notes.md; rm untracked.tmp

# =============================== --f scope (whole branch + lease) ======================
check "--f scope on a side branch = BASE"           '[ "$(scope_for --f)" = "$BASE" ]'
OLD=$(git rev-parse HEAD)
git reset -q --soft "$BASE" && git reset -q
git add api/band.ts;   git commit -q -m "feat(api): band"
git add ui/chip.ts;    git commit -q -m "feat(ui): chip uses band"
git add docs/notes.md; git commit -q -m "docs: band"
check "--f regroup: 5 wip -> 3 concern commits"      '[ "$(git rev-list --count "$BASE"..HEAD)" = 3 ]'
check "--f regroup: content identical to OLD"        'git diff --quiet "$OLD" HEAD'
ok=1; for sha in $(git rev-list --reverse "$BASE"..HEAD); do git checkout -q "$sha"; ./check.sh >/dev/null || ok=0; done; git checkout -q feat/x
check "--f: every intermediate commit passes typecheck (api before ui)" '[ $ok = 1 ]'
git push -q --force-with-lease=feat/x:"$REMOTE" "$R" feat/x
check "--f: force-with-lease accepted, remote now at HEAD" '[ "$(git rev-parse stylit/feat/x)" = "$(git rev-parse HEAD)" ]'

# =============================== guards ==================================================
# 1) wrong order breaks bisectability: ui before api must fail the per-commit check
git reset -q --soft "$BASE" && git reset -q
git add ui/chip.ts;    git commit -q -m "feat(ui): chip uses band"
git add api/band.ts;   git commit -q -m "feat(api): band"
git add docs/notes.md; git commit -q -m "docs: band"
ok=1; for sha in $(git rev-list --reverse "$BASE"..HEAD); do git checkout -q "$sha"; ./check.sh >/dev/null || ok=0; done; git checkout -q feat/x
check "guard: ui-before-api ordering is caught by the per-commit typecheck" '[ $ok = 0 ]'
git reset -q --hard stylit/feat/x

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
cd "$WORK"; LEASE=$(git rev-parse stylit/feat/x)   # what we last saw
git commit -q --allow-empty -m "chore: local only"
git push -q --force-with-lease=feat/x:"$LEASE" "$R" feat/x 2>/dev/null && pushed=1 || pushed=0
check "guard: lease rejected when remote moved underneath us" '[ $pushed = 0 ]'
git fetch -q "$R"
check "guard: after fetch, REMOTE not ancestor of HEAD -> skill must stop" '! git merge-base --is-ancestor "$(git rev-parse @{u})" HEAD'
git reset -q --hard "$R/feat/x"

# 4) merge commit in range -> stop
git checkout -q main; commit README.md "main moved" "chore: main moved"; git push -q "$R" main
git checkout -q feat/x; git merge -q --no-edit main >/dev/null
check "guard: merge commit in BASE..HEAD detected" '[ -n "$(git rev-list --merges "$(git merge-base HEAD main)"..HEAD)" ]'

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
check "default branch, no upstream: scope is HEAD, step 7 skips"  '[ "$(scope_for)" = "$(git rev-parse HEAD)" ]'
git branch -q -u "$R/$DEF"; git reset -q --hard "$PUSHED"
git checkout -q --detach
check "guard: detached HEAD -> refuse" '[ "$(git rev-parse --abbrev-ref HEAD)" = HEAD ]'

# =============================== step 7b: merge (`m`) ====================================
# Replays the skill's merge method: pre-checks, sync target, ff-or-merge-commit, gate, delete branch.
merge_step() { # merge_step <feature> <target> <gate cmd> -> sets MERGED (1/0), TARGET_OLD, FEATURE_SHA
  local target=$2 tu
  git rev-parse --verify -q "refs/heads/$target" >/dev/null || return 1
  [ "$(git rev-parse --abbrev-ref HEAD)" != "$target" ] || return 1
  tu=$(git rev-parse --abbrev-ref "$target@{u}" 2>/dev/null)
  if [ -n "$tu" ]; then git fetch -q "${tu%%/*}"; git merge-base --is-ancestor "$target" "$tu" || return 1; fi
  [ -z "$(git status --porcelain --untracked-files=no)" ] || return 1
  git checkout -q "$target"; [ -n "$tu" ] && git merge -q --ff-only "@{u}"
  TARGET_OLD=$(git rev-parse HEAD)
  git merge -q --ff-only "$1" 2>/dev/null || git merge -q --no-ff --no-edit "$1"
  if $3 >/dev/null; then FEATURE_SHA=$(git rev-parse "$1"); git branch -q -d "$1"; MERGED=1
  else git reset -q --hard "$TARGET_OLD"; git checkout -q "$1"; MERGED=0; fi
}

# 1) happy path: regroup, then fast-forward into the default branch
git checkout -q main; git checkout -q -b feat/m1
commit docs/m1.md "m1" "wip: m1"; commit docs/m1.md "m1 v2" "wip: m1 v2"
OLD=$(git rev-parse HEAD); git reset -q --soft "$(git merge-base HEAD "$DEF")" && git reset -q
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

# 4) pre-checks: target ahead of its upstream, or current branch is the target -> refuse
git checkout -q main; git commit -q --allow-empty -m "chore: local-only on main"; git checkout -q feat/m3
check "m guard: target ahead of upstream -> refuse"     '! merge_step feat/m3 "$DEF" ./check.sh && [ "$(git rev-parse --abbrev-ref HEAD)" = feat/m3 ]'
git checkout -q main
check "m guard: on the target branch -> refuse"         '! merge_step main "$DEF" ./check.sh'

printf '\n%s\n' "$([ $FAILS = 0 ] && echo 'ALL PASS' || echo "$FAILS FAILED")"
[ $FAILS = 0 ]
