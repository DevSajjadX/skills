---
name: maintenance-routines
description: Use when asked to run an autonomous maintenance pass over one scope of a codebase and prove each change before it lands - removing dead or unused code, unifying duplicated logic, fixing a test that sometimes fails (flaky), finding code that contradicts its documented intent (logic bugs), simplifying convoluted code without changing behaviour, or pruning tests that can never fail. Not for a bug the user can already reproduce (debug it directly), for a feature, for missing coverage, or for a test that fails every time (that is a real bug).
category: Maintenance
tags: [routine, maintenance]
---

# Maintenance routines

One family of autonomous maintenance passes over a single scope: **discover, prove, fix, verify, commit**, one finding at a time. This file is the contract every routine shares. Each routine file adds only what its defect class needs. A rule that applies to more than one routine lives here; a routine file that restates it has forked the contract.

## Pick the routine

Match the request to one row, then read **exactly that one file** next, not the others. If nothing fits, say so; do not stretch a routine to cover it.

| Request or symptom | Routine file |
| --- | --- |
| Code nothing can reach (unused, unreachable, orphaned) | [dead-code-removal.md](dead-code-removal.md) |
| Two live copies of the same rule inside one module | [dup-unifier.md](dup-unifier.md) |
| A test that sometimes fails, or passes on rerun | [flaky-test-fixer.md](flaky-test-fixer.md) |
| Behaviour provably wrong against its documented intent, including crashes found by reading | [logic-bugfixer.md](logic-bugfixer.md) |
| Live, single, reachable code that is convoluted | [logic-simplifier.md](logic-simplifier.md) |
| A test that can never fail | [useless-test-pruner.md](useless-test-pruner.md) |

## Preconditions: verify once, up front

1. Check the current branch. A routine works on its own branch, never the default branch. If on the default branch, create `routine/<name>-<scope>`, or STOP and ask.
2. Check `git status`. Uncommitted work you did not do belongs to another session: surface it and ask. Never sweep unrelated changes into a routine's commits.
3. Read the project's `AGENTS.md` or `CLAUDE.md`, and any list of things it says must not be done (a "do not do" file, a decision log). Anything it forbids is a hard STOP for any finding that would conflict, however small the diff.
4. Read the scope's own notes: the nearest `AGENTS.md`, module README or architecture note. Its "rules a compiler will not catch" section (or equivalent) is exactly the list of things that look like defects and are not.

## Scope

`$ARGUMENTS` names a scope: one module, package, directory or feature. When empty, survey the project's scopes, pick the single highest-value target, and announce the pick with a one-line plan before doing any work.

**Every finding stays inside one scope.** A finding that spans two modules is not a bigger fix. It is a boundary question, which is a STOP.

## Proof standard

Never fix on suspicion. A detector hit, a grep match or a hunch is a **candidate**; each routine defines what counts as **proof**: a failing test, a still-green sabotaged test, an empty reference sweep, a reproduction. No proof, no fix. Report the candidate as skipped, with what proof was missing.

The proof is pasted output, not an assertion that you ran something. A filtered gate (`... | grep -v`) is a passing grep, not a passing check.

## Verify gates: never commit red

The gate is the project's own full check list, verbatim, as its `AGENTS.md` or `CLAUDE.md` names it (test, lint, type-check, build). A routine may skip the part of the list its scope cannot affect, but it names what it skipped and why. Before the last commit, run the project's own secret scanner if it names one.

**If no automated check covers the changed behaviour, STOP and report the finding instead of committing it.** That is the whole point of a proof standard.

## Branch and commit protocol

There is no shipping step here. The routine works on its own branch and stops at commits. Pushing, opening a PR and merging are the user's call (the `wrap` skill does them).

**One finding per commit.** Commit each proven, verified finding on its own, with a conventional subject that names it, before starting the next, so reverting one commit undoes one cleanup alone. Stage exactly the files you touched; never stage everything blindly.

## Budget

**3 committed findings per invocation**, then stop and summarize:

- **committed**: the branch name, then each finding's commit SHA, one line each
- **found but skipped**: each with its reason: no proof, a STOP condition, out of budget
- **nothing found**: say so plainly. An empty pass is a valid, useful result; manufacturing a finding to justify the run is the failure mode this budget exists to prevent.

## Universal STOPs

Report, do not fix:

- The fix needs a **new dependency**, module, architecture decision record or tool server. Ask first.
- The fix touches a **cross-module contract**: a shared interface, public API surface or published package another module or repo consumes.
- The fix **renames an error class or code** that is a wire key, so every client branching on it breaks.
- The fix **changes a route or path constant** that callers and tests rely on.
- The finding spans two modules, or wants a third module's data.
- The fix changes behaviour that no test pins and that cannot be safely pinned first.
- The finding conflicts with something the project says not to do.
- A gate goes red and you cannot root-cause it.
- The code carries a marker saying the shortcut is deliberate and ledgered (a `DEBT #N` comment or equivalent). Retiring it is its own change.

A STOP is not a failure. It is a **handoff**. Write it to `.claude/handoffs/` through the `plan-handoff` skill and name it in the summary. The board or backlog is never written by a routine.

## Never touch

- Generated code and generated API clients or specs: regenerate them with the project's generator, never edit.
- Applied database migrations: an applied migration is never edited; schema changes come from the project's own migration path.
- The project's board or backlog (for example `.pm/**`): `product-manager` is its only writer. A routine that finds work writes a handoff.
- Lockfiles, toolchain pins, `.env*`, or anything secret-shaped.
- Architecture decision records: amending an invariant is an ADR change, which is ask-first.
- The agent instruction files (`AGENTS.md`, `CLAUDE.md`) and skill folders.

## Symptom to owner

When you find something outside your defect class, do not fix it. Note it in the summary and defer to its owner:

| Symptom | Owner |
| --- | --- |
| Code nothing can reach | [dead-code-removal.md](dead-code-removal.md) |
| Two live copies of the same logic in one module | [dup-unifier.md](dup-unifier.md) |
| Behaviour provably wrong, including crashes | [logic-bugfixer.md](logic-bugfixer.md) |
| Live, single, reachable, but convoluted | [logic-simplifier.md](logic-simplifier.md) |
| A test that can never fail | [useless-test-pruner.md](useless-test-pruner.md) |
| A test that sometimes fails | [flaky-test-fixer.md](flaky-test-fixer.md) |
| Tests of code being deleted | travel with their code |
| Two live copies across modules | STOP: a module-boundary design question, handoff |
| A rule stated in prose that a check could hold | a handoff |

## Arguments

$ARGUMENTS
