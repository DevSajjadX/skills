---
name: wrap
description: "Use when the user asks to wrap up, finish or close out the session, or to commit, push, squash/regroup commits, or merge the branch — and before any git commit, which goes through wrap."
argument-hint: "[c|commit [--p]] [s|squash [--p|--f]] [m|merge [branch] [--p|--f]]"
---

# Wrap the session

Close out the session so the repo is clean, verified, and ready to commit. Work the steps in order; each ends on its criterion.

## Arguments

`/wrap $ARGUMENTS` — bare words, any order; `--p` only after `c`, `s` or `m`, `--f` only after `s` or `m`; `--p` implies `c`; `m` implies `s` (and `c`, so the tree is clean to merge). Bare `/wrap` = steps 1–9, step 7 only when its trigger fires (local scope), step 8 draft-only.

**A primary that cannot run revokes its modifiers.** `--p` and `--f` are sub-orders of `c`, `s` or `m`. When the primary stops for any reason (a guard, a failed pre-check, an AskUserQuestion answered or defaulted to stop), wrap stops and reports: no modifier, and no later one-way step, a push above all. Pushing after a refused squash spends the locality the squash needed and turns a free local `reset --soft` into a force push.

The model picks the arguments from what the user asked — "commit" → `c`, "push" → `--p`, "squash"/"regroup" → `s`, "merge" → `m` — and runs the skill itself. Never tell the user to type `/wrap …`, and never ask permission for a plain commit or fast-forward push. Wrap asks only where it cannot choose for you: which default branch (step 2, when nothing names it), which remote (several, no upstream), how to group files that need hunk splits (step 7), and the `--f` force push.

- `commit` / `c` — step 8 commits (explicit paths). Unpushed commits are reported under Needs you, not asked about.
- `--p` — after step 8's commit(s), push: `git push <remote> <branch>`, fast-forward only, never bare `--force`. With `s`, the regrouped commits are what gets pushed (local scope, so always a fast-forward). Remote = the upstream's (`git rev-parse --abbrev-ref @{u}` → `<remote>/<branch>`); no upstream → `-u` to the sole remote, ask if several. Remote rejects → stop and report; never force. With `m`, the branch pushed is the *target*, after step 7b's merge. Primary stopped → no push (rule above).
- `squash` / `s` — step 7 runs regardless of the pattern check; local scope.
- `s --f` — step 7 covers the whole branch since its merge-base with the default branch, pushed commits included, then pushes with `--force-with-lease` (`--p` is redundant here). Asks once before the reset. Only for side branches nobody else has open work or reviews on; refused on the default branch (step 7).
- `merge` / `m [target]` — `s`, then step 7b merges the branch into `target` (default: `$DEF` from step 2, never a hardcoded `main`) and deletes the local feature branch. Fast-forward when possible, else one merge commit; never squash-merge — the regrouped commits are the history.
- `m --f` — `s --f` (whole-branch regroup, the one AskUserQuestion, `--force-with-lease` push), then step 7b. `--p` here pushes `target`.

## 1. Sweep

Review everything the session touched: `git status`, then the full diff (staged, unstaged, untracked). Remove scratch files, debug output, commented-out code, and stubs. Every leftover is either deleted or promoted to real, named work.

Also sweep the runtime: kill any process, container, or simulator session **this session spawned** and no longer needs. Leave the user's own long-running processes (their dev servers, their simulator) untouched — name them in the report's Needs-you/heads-up instead.

Done when every modified and untracked file is accounted for (kept on purpose or gone) and no agent-spawned process is left running unreported.

## 2. Review

Refs (step 7 reuses them):
- `UP=$(git rev-parse --abbrev-ref @{u} 2>/dev/null)` (`<remote>/<branch>`); `R=${UP%%/*}`, or the sole remote when no upstream — never assume `origin`.
- `DEF=$(git symbolic-ref --short refs/remotes/$R/HEAD 2>/dev/null)`, strip `$R/`; empty → the remote's own answer, `git ls-remote --symref $R HEAD` (`ref: refs/heads/<b>`); still empty → the one of `main`/`master` that exists locally; neither or both → stop and ask. Never go on with an empty `DEF`: the empty `$SCOPE` it leads to makes `git diff --quiet $SCOPE $TREE` pass and skips the review in silence.
- `REMOTE=$(git rev-parse @{u} 2>/dev/null)`, else the same-name `refs/remotes/$R/<branch>` when it exists — a push without `-u` is still a push.
- `BASE=$(git merge-base HEAD $DEF $R/$DEF)`, naming only those of the two that exist: the newest commit HEAD shares with either copy of the default branch, so a local `$DEF` behind or ahead of its remote never brings default-branch commits into range. On `$DEF` itself it is HEAD.
- `SCOPE`: `--f` → `$BASE` (off `$DEF` only; step 7 refuses it there). Otherwise the parent of the oldest commit no remote has: `U=$(git rev-list HEAD --not --remotes $DEF | tail -1)` (`$DEF` only off it and when it exists locally), `SCOPE=$U^` — a plain run never reaches a pushed commit, upstream or not, nor, off `$DEF`, a local default-branch commit. `U` empty, or a root commit (no remote has any of it) → HEAD's sha; in the root case step 7 skips, as nothing marks where the unpushed work begins.
- `TREE=$(GIT_INDEX_FILE=$(mktemp -u) sh -c 'git read-tree HEAD && git add -A && git write-tree; rm -f "$GIT_INDEX_FILE"')` — a tree object of the working tree, untracked included, ignored excluded; the real index and tree stay untouched. It is exactly what wrap will commit, so it is what gets reviewed.

`git diff --quiet $SCOPE $TREE` → nothing to review, skip. Otherwise run the `reviewing-changes` skill (Skill tool) with base `$SCOPE` and head `$TREE`. `$TREE` is not a commit, so two-argument forms only: `git diff $SCOPE $TREE`, `git grep … $TREE --`, and the skill's own sweep with `$SCOPE $TREE` as base and head; the commit list is `git log --oneline $SCOPE..HEAD`. Claims = what the session set out to do plus every commit message in that range. Skill not installed → say so under Needs you and continue.

The review names, wrap fixes — apply the findings instead of reporting them:
- BLOCK / HIGH: fix now; nothing commits while one stands.
- MED / LOW and every sweep row with an `existing:` hit: fix (reference the existing constant, helper, bulk call, doc) unless the fix outgrows the session's change → carry it into step 3 as declared debt.
- Re-run the review after fixing (fresh `$TREE`); after two passes, report what remains instead of a third.

Done when the verdict is MERGE, or MERGE WITH DECLARED DEBT with every item carried into step 3; or the review was skipped (empty diff, or the skill is missing and noted under Needs you); or two passes ran and what remains is reported. Then continue through step 9 — a standing BLOCK/HIGH still blocks every commit (above).

## 3. Retire debt

Ship correct-by-design code. The review's Declared-debt rows and undeclared-debt findings are the input. A shortcut that must stay is declared: name it, its ceiling, and the follow-up that retires it, both in the final report and wherever the project tracks work.

Done when the diff holds no shortcut the report leaves unnamed.

## 4. Let the code speak

The code is the source of truth. A comment survives only when it states what code cannot: an external-system fact or a cross-module invariant. Prefer a rename, a named constant, or an assertion; delete narration of what the next line does or why the change is right.

Done when every comment in the diff passes that test.

## 5. Sync the docs

Update the docs the change made stale (README, ADRs, project guides), starting from the review's doc hits. Details of the change belong here, not in the commit message.

Done when every behavior change is reflected in docs, or the report says why none apply.

## 6. Go green

Run the project's own gates: tests, typecheck, lint, whatever the repo defines. Fix what fails.

Done when the gates pass and the report quotes the commands run.

## 7. Squash (careful)

Trigger: local per-task commits that don't match the default branch's pattern (read its `git log` for the last comparable body of work), on any run; `s` runs it regardless. The guard is pushed commits, not the branch's name: plain `s` stops at `$SCOPE`, touching only commits no remote has seen, so it runs on the default branch too. `--f` reaches through pushed commits, so it is for side branches only (pre-checks).

Pre-checks (refs from step 2):
- Detached HEAD (`git symbolic-ref -q HEAD` fails) → stop.
- `$REMOTE` set but not an ancestor of HEAD → stop; sync first.
- `git rev-list --merges $BASE..HEAD` non-empty → stop; a soft reset flattens merges silently.
- `--f` on `$DEF` → stop; `$BASE` is HEAD there, and the default branch's published history is not `--f`'s to rewrite. Report that plain `s` regroups its unpushed commits.

Scope: `$SCOPE` from step 2. `--f` = `$BASE`, after ONE AskUserQuestion — proceed with force push / local-only instead / stop; auto-continues with no answer → stop, never force push without an explicit choice. With `c` (so also `--p` and `m`), step 8's commit runs now, its push not yet: those commits join the regroup, and 7b finds a clean tree. Then nothing committed above scope → skip.

A soft reset regroups at file granularity — true per-concern commits come from committing per concern during the session; wrap only tidies.

Method (no interactive rebase):
1. Without `c`, park uncommitted wrap edits: `S0=$(git rev-parse -q --verify refs/stash)`, then `git stash push -q` (tracked only — untracked files don't affect a soft reset and may be large tool output). Parked only when `refs/stash` moved off `$S0`: a clean tree stashes nothing, and a blind pop would apply the user's own stash. Pop only what was parked, after 6 (after any `--f` verify and push), also on abort — step 6's checkouts need a clean tree, and its `reset --hard $OLD` would wipe popped edits.
2. `OLD=$(git rev-parse HEAD)`; `git reset --soft <scope> && git reset`.
3. One `git add <explicit paths>` + commit per concern, mirroring the default branch's grouping and order, dependencies first (schema → api → ui → e2e/docs) so the branch bisects. Each commit is one united change that stands alone and typechecks — merge a group that can't into the one it needs; never squash merely for fewer commits. Files that don't partition without hunk splits → ask: merge groups / keep separate / stop. Each `git commit` is its own Bash call, never the tail of a chain, so the commit gate's "rerun the exact command" replays only the commit.
4. Messages per step 8.
5. `git diff --quiet $OLD HEAD` must pass, else `git reset --hard $OLD`, report, stop.
6. `--f` only: verify each intermediate commit — `git checkout <sha> && <typecheck command>` per commit, then `git checkout <branch>`; a failure → merge that group into the one it needs and redo from 2, or `git reset --hard $OLD` and stop. Then, with `$REMOTE` set: `git push --force-with-lease=<branch>:$REMOTE $R <branch>`. Rejected → stop; never `--force`.

Mechanics of this step and the step 2 refs/`$TREE` snapshot are exercised by `tests/dry-run.sh` (throwaway repo, bare remote, both scopes, every guard); run it after editing step 2's refs, this step or 7b. Its replay is a copy: a parity FAIL names a command reworded here, whose replay helper changes with it. `tests/gate.sh` exercises the commit-gate hook; run it after editing the hook.

Report: old hashes gone; `git reset --hard <OLD>` (print the hash) undoes the regroup until garbage collection; whether intermediate commits were typecheck-verified (local runs: ordered for bisectability, unverified unless you ran them). After `--f`: other checkouts recover with `git fetch && git reset --hard $R/<branch>`. Plain `s` with pushed commits above `$BASE`: mention `s --f` can regroup those too.

## 7b. Merge (`m` only)

Runs after step 7's parity check (`git diff --quiet $OLD HEAD`) and after any `--f` push. `target` = the argument, else `$DEF`.

Pre-checks — any failure → stop, report, nothing merged:
- Current branch is not `target`; `target` exists locally (`git rev-parse --verify refs/heads/<target>`).
- `TU=$(git rev-parse --abbrev-ref <target>@{u} 2>/dev/null)`; when set: `git fetch ${TU%%/*}` and `git merge-base --is-ancestor <target> $TU` — `target` at or behind its upstream, else stop (local-only commits on `target` are not wrap's to merge over).
- `git status --porcelain --untracked-files=no` empty — wrap edits are committed by now; untracked wrap output is fine.

Method:
1. `FEATURE=$(git rev-parse --abbrev-ref HEAD)`; `FEATURE_UP=$(git rev-parse --abbrev-ref $FEATURE@{u} 2>/dev/null)` (recorded now: deleting the branch drops its upstream config, and the report needs it); `git checkout <target>`; with upstream `git merge --ff-only @{u}` (sync first); `TARGET_OLD=$(git rev-parse HEAD)`.
2. `git merge --ff-only $FEATURE`, else `git merge --no-ff --no-edit $FEATURE`. Never squash-merge.
3. Step 6's gate commands on the merged result. Failure → `git reset --hard $TARGET_OLD && git checkout $FEATURE`, report, stop. Nothing is deleted or pushed.
4. `FEATURE_SHA=$(git rev-parse $FEATURE)`; `git merge-base --is-ancestor $FEATURE HEAD && git branch -D $FEATURE` — the check is the real question, is it in `target`; `-d` asks the feature's upstream instead and refuses a pushed branch with local commits. Check fails → stop, report. Stay on `target`. `--p` → push `target` per the `--p` rules (fast-forward only).

`tests/dry-run.sh` exercises this step too (ff merge, merge commit, gate-failure rollback, `m` with only uncommitted work, a pushed feature).

Report: target and merge kind (fast-forward or merge commit); `git reset --hard <TARGET_OLD>` (print the hash) undoes the merge; `git branch <FEATURE> <FEATURE_SHA>` restores the deleted branch until garbage collection; whether `target` was pushed. `FEATURE_UP` set → the remote feature branch still exists, stale unless `--f` pushed it — deleting it is the user's call (Needs you).

## 8. Commit message

For changes still uncommitted after step 7 (with `c`, the commit already ran at step 7's scope check whenever step 7 ran; the push is still this step's). Readable by humans and LLMs: `type(scope): subject` ≤ 72 chars; body a few lines — what changed and why, pointing to the docs from step 5; one united change per commit, split when changes span concerns; match recent `git log` style. Draft only; with `c`, commit with explicit paths, then push if `--p` and the primary did not stop (Arguments). The commit runs as its own Bash call for the same reason.

## 9. Report

End with two sections:

- **Landed**: one line per meaningful change, the review verdict, the gate results, the commits made or the message draft, the merge (step 7b) when `m` ran.
- **Needs you**: anything only the user can decide or do (migrations, env vars, manual settings, debt follow-ups from step 3). "Nothing" is a valid answer.

End every wrap with this help block:

```
/wrap            sweep · review · docs · gates · regroup unpushed if messy · draft only
/wrap c|commit   + commit
/wrap c --p      + commit and fast-forward push
/wrap s|squash   regroup local commits by concern
/wrap s --p      regroup, commit, fast-forward push
/wrap s --f      whole branch, then --force-with-lease (asks first)
/wrap m [branch] regroup, then merge into branch (default: the default branch)
/wrap m --f      whole-branch regroup + --force-with-lease, then merge
```
