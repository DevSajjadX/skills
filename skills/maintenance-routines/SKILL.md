---
name: maintenance-routines
description: Use when asked to run an autonomous maintenance pass over one scope of a codebase and prove each change before it lands - removing dead or unused code, unifying duplicated logic, fixing a test that sometimes fails (flaky), finding code that contradicts its documented intent (logic bugs), simplifying convoluted code without changing behaviour, or pruning tests that can never fail ("only test their own mocks", "our coverage is fake", "slim the test suite"). Not for a bug the user can already reproduce (debug it directly), for a feature, for missing coverage, or for a test that fails every time (that is a real bug).
argument-hint: "[routine] [scope, or for flaky-test-fixer a log or test name]"
category: Maintenance
tags: [routine, maintenance]
---

# Maintenance routines

One family of autonomous maintenance passes over a single scope: **discover, prove, fix, verify, ship**, one finding at a time. This file is the contract every routine shares. Each routine file adds only what its defect class needs. A rule that applies to more than one routine lives here; a routine file that restates it has forked the contract.

**These passes often run unattended** (scheduled, overnight, from a queue), with nobody to answer a question. Everything below is written so a run can finish alone: where a rule says "STOP and ask", an unattended run does not wait. It writes the handoff, skips that finding and moves to the next one or ends. Where the project has its own rule ids (a numbered convention list, a decision record), cite the id when you cite the rule, so the next reader can look it up.

## Pick the routine

Match the request to one row, then read **exactly that one file** next, not the others. The same table routes a finding outside your class: note it in the summary and defer to its row, never fix it. If nothing fits, say so; do not stretch a routine to cover it.

| Request or symptom | Routine file |
| --- | --- |
| Code nothing can reach (unused, unreachable, orphaned) | [dead-code-removal.md](dead-code-removal.md) |
| Two live copies of the same rule inside one module | [dup-unifier.md](dup-unifier.md) |
| A test that sometimes fails, or passes on rerun | [flaky-test-fixer.md](flaky-test-fixer.md) |
| Behaviour provably wrong against its documented intent, including crashes found by reading | [logic-bugfixer.md](logic-bugfixer.md) |
| Live, single, reachable code that is convoluted | [logic-simplifier.md](logic-simplifier.md) |
| A test that can never fail | [useless-test-pruner.md](useless-test-pruner.md) |
| Tests of code being deleted | travel with their code |
| Two live copies across modules | STOP: a module-boundary design question, handoff |
| A rule stated in prose that a check could hold | a handoff |

## Preconditions: verify once, up front

1. Check the current branch (`git branch --show-current`). A routine works on its own branch, never the default branch, and a ship command usually refuses the default branch anyway. If on the default branch, create `routine/<name>-<scope>`, or STOP and ask.
2. Check `git status`. Uncommitted work you did not do belongs to another session: surface it and ask. Never sweep unrelated changes into a routine's commits or ship.
3. Read the project's `AGENTS.md` or `CLAUDE.md`, and any list of things it says must not be done (a "do not do" file, an anti-goals list, a decision log). Anything it forbids is a hard STOP for any finding that would conflict, however small the diff.
4. Read the scope's own card: the nearest `AGENTS.md`, module README or architecture note (for a backend module, the kernel or a frontend feature folder, its own file). Its "rules a compiler will not catch" section (or equivalent) is exactly the list of things that look like defects and are not.

## Scope

`$ARGUMENTS` is `[routine] [scope]`. If the first word matches a routine in the table above, it picks that routine and the rest is the scope (for `flaky-test-fixer`, the rest is a failing log or a test name). With no routine named, pick one from the request's symptom, or ask. Never run more than one routine per invocation.

A scope is one module, package, directory or feature, and the valid scopes are **the project's own scope list**: the modules, shared kernel or library, and frontend feature folders its `AGENTS.md` or `CLAUDE.md` names (with the path pattern each lives under). If the project names none, a scope is one top-level package or directory. When the scope is empty, survey the project's scopes in the order its instruction file gives (otherwise most-changed and most-business-critical first), pick the single highest-value target, and announce the pick with a one-line plan before doing any work.

**Every finding stays inside one scope.** A finding that spans two modules is not a bigger fix. It is a boundary question, which is a STOP.

## Proof standard

Never fix on suspicion. A detector hit, a grep match or a hunch is a **candidate**; each routine defines what counts as **proof**: a failing test, a still-green sabotaged test, an empty reference sweep, a reproduction. No proof, no fix. Report the candidate as skipped, with what proof was missing.

The proof is pasted output, not an assertion that you ran something. A filtered gate (`... | grep -v`) is a passing grep, not a passing check.

## Verify gates: never ship red

The gate is the project's own full check list, verbatim, in full, as its `AGENTS.md` or `CLAUDE.md` names it. It is usually one aggregate command (`pnpm gates`, `make check`, `just ci`, `uv run poe check`) or a short list (test, lint, type-check, format, build, repo checks). Run what the file says; never invent a lighter list.

A routine may skip the part of the list its scope cannot affect (a frontend-only change does not need the backend formatter, a docs-only scope needs no build) by naming the gates it runs (for example `make check-frontend check-repo`), but it names what it skipped and why. Before every ship, and before the last commit when there is no ship, run the project's own secret scanner if it names one (for example `gitleaks dir . --redact`).

**If no automated check covers the changed behaviour, STOP and report the finding instead of shipping it.** That is the whole point of a proof standard.

## Ship protocol

**One finding per commit.** Commit each proven, verified finding on its own, with a conventional subject that names it, before starting the next, so reverting one commit undoes one cleanup alone. Stage exactly the files you touched; never stage everything blindly. Several findings in one commit, or a rename, a reorder and a fix in one commit, cannot be reviewed or reverted piece by piece.

**One shipment per run.** After the gates pass over all of the run's commits, ship them together, once:

- **The project has a ship or PR command** (a `/ship` skill, a `make pr`, a documented script) **and its instruction file names it, and this run is authorized to use it** (the request asks to ship or open a PR, or the instruction file says routines ship through it): compose that command. It opens the PR (in projects where that command is the only path to the default branch, it is also where the gates run). You made the changes in this session, so run it session-aware: stage exactly the files you touched, write the message from what you know. One finding per commit, one PR per run, never one PR per finding.
- **Otherwise** (no such command, or the run is not authorized to use it): stay on your own `routine/<name>-<scope>` branch with one commit per finding, and **do not push**. Pushing, opening a PR and merging are the user's call (the `wrap` skill does them).

## Budget

**3 shipped findings per invocation** (a committed finding when the run does not ship). One routine runs per invocation, so this is the per-routine budget. When it is spent, stop and summarize:

- **shipped**: the run's PR URL and merged SHA when a ship command ran, otherwise the branch name; then each finding's commit SHA, one line each
- **found but skipped**: each with its reason: no proof, a STOP condition, out of budget
- **nothing found**: say so plainly. An empty pass is a valid, useful result; manufacturing a finding to justify the run is the failure mode this budget exists to prevent.

## Universal STOPs

Report, do not fix:

- The fix needs a **new dependency**, module, architecture decision record or tool server (an MCP server entry, a new detector or linter). Ask first.
- The fix touches a **cross-module contract**: a shared interface, a module's published contracts project, a public API surface or a published package another module or repo consumes. That is a door between modules, not a cleanup.
- The fix **renames an error class or code** that is a wire key, so every client branching on it breaks.
- The fix **changes a route or path constant** that callers and tests rely on.
- The finding spans two modules, or wants a third module's data.
- The fix changes behaviour that no test pins and that cannot be safely pinned first.
- The finding conflicts with something the project says not to do.
- A gate goes red and you cannot root-cause it.
- The code carries a marker saying the shortcut is deliberate and ledgered (a `DEBT #N` comment or equivalent). Retiring it is its own change.

A STOP is not a failure. It is a **handoff**, and it is the correct result of an unattended run that hit one. Write it to `.claude/handoffs/` through the `plan-handoff` skill and name it in the summary. The board or backlog is never written by a routine.

## Never touch

- Generated code and generated API clients or specs: regenerate them with the project's generator, never edit.
- Applied database migrations: an applied migration is never edited; schema changes come from the project's own migration path.
- The project's board or backlog (for example `.pm/**`): `product-manager` or the project's own board skill is its only writer. A routine that finds work writes a handoff.
- Lockfiles, toolchain pins (an SDK version file, `.python-version`, `.nvmrc`), `.env*`, or anything secret-shaped.
- Architecture decision records: amending an invariant is an ADR change, which is ask-first.
- The agent instruction files (`AGENTS.md`, `CLAUDE.md`, including a `CLAUDE.md` that only includes `AGENTS.md`), the project's root product or design documents, and skill folders or their link targets (a repo check may keep them in sync).

## Arguments

$ARGUMENTS
