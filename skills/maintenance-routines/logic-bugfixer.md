# Routine: logic bugfixer

Shared rules (preconditions, scope, proof standard, gates, branch and commit protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to wrong behaviour.

## The defect

Code that **provably contradicts its documented intent**. Not code you would have written differently. Code that does something its own documentation says it must not.

"Documented intent", in priority order:

1. **Architecture decision records** (`docs/adr/` or equivalent): invariants a compiler cannot hold.
2. **The project's convention rules**, where they carry ids or names.
3. **The scope's `AGENTS.md`**: its "rules a compiler will not catch" section.
4. **The glossary** (`CONTEXT.md` or equivalent): a term used to mean something it does not.
5. **Docstrings and comments at the code**: the text that says what the function guarantees.

A gap between code and a doc is not automatically a code bug. When two documents disagree (a docstring against an ADR), the higher one in this list wins. When the doc is the stale one, the fix is the doc, which is a documentation change, not a code change. **Decide which is wrong before you fix either.** Fixing a stale comment is its own finding: it needs no failing test, only the higher-ranked source quoted.

## Where to look first

Read the project's history and notes for places it has already been bitten, and start there. Typical hot spots: boundary conditions (inclusive against exclusive bounds, `>` against `>=`), rounding and money, paging cursors, tenant or permission filters, transaction boundaries, state transitions that skip their one owner, locale and display formatting.

## Prove

The proof is a **failing test that names the wrong behaviour**, written before the fix:

1. Write the test asserting the documented intent.
2. Run it. **It must fail**, and fail for the stated reason. Read the failure; do not assume it. A test that fails because of a typo in the test proves nothing.
3. Fix the cause. Not the symptom: if the wrong value arrives from two layers up, the fix is two layers up, even when a local guard would make the test green.
4. Run it again. It passes, and the whole suite still passes.

A candidate you cannot turn into a failing test is **not a finding**. Report it as skipped with what you could not reproduce. That is honest and useful; a speculative fix is neither.

## Fix

- Fix the **cause**. A guard added at the symptom leaves the bug live for every other caller.
- If the cause is in another module, that is a STOP: write a handoff naming the `file:line` and the failing test you wrote, so the next session starts from evidence.
- Keep the diff to the bug. A drive-by rename in a bugfix hides the fix in the diff.

## Verify

The project's full gate list, plus:

- The new test fails on the pre-fix code (paste both runs: red then green).
- The full suite passes.
- No other test changed. A test you had to edit to make green means the behaviour change was wider than the bug: stop and explain it.

## Specific STOPs

Beyond the universal list:

- **The "bug" is a documented decision.** Read the scope's card first. Several things look wrong and are not (a deliberate cross-tenant read, an identical answer given to avoid leaking whether an account exists).
- **The doc is the stale one.** Fix the doc and say so. Do not change working code to match a sentence nobody updated.
- **The fix changes an error key or a route constant.** Ask first.
- **The fix amends an ADR.** That is a design decision with a human in it.
- **The behaviour is wrong only under a race you cannot reproduce.** Report it; a fix with no failing test is a guess with a commit message.

## Summary

Per the budget block: committed (branch, SHAs, with the red-then-green evidence), skipped (with what you could not reproduce), or nothing found.
