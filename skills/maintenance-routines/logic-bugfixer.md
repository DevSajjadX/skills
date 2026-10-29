# Routine: logic bugfixer

Shared rules (preconditions, scope, proof standard, gates, ship protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to wrong behaviour.

## The defect

Code that **provably contradicts its documented intent**. Not code you would have written differently. Code that does something its own documentation says it must not.

"Documented intent", in priority order:

1. **Architecture decision records** (`docs/adr/` or equivalent): invariants a compiler cannot hold.
2. **The project's convention rules**, where they carry ids or names.
3. **The scope's `AGENTS.md`**: its "rules a compiler will not catch" section.
4. **The glossary** (`CONTEXT.md` or equivalent): a term used to mean something it does not.
5. **Docstrings and comments at the code**: the text that says what the function guarantees.

A gap between code and a doc is not automatically a code bug. When two documents disagree (a docstring against an ADR), the higher one in this list wins. **Code is truth**: when the doc is the stale one, the fix is the doc, which is a documentation change, not a code change. A stale ADR, `AGENTS.md` or `CLAUDE.md` is never-touch: write a handoff that quotes the code and the stale line. Only docstrings, comments and the glossary are fixed here. **Decide which is wrong before you fix either.** Fixing a stale comment is its own finding: it needs no failing test, only the higher-ranked source quoted. The doc fix goes through the project's own documents skill or process when it has one.

## Where to look first

Defects cluster in a few places, and the project has usually been bitten in some of them already. **The project's instruction file may name its own hot spots** (a "where we have been bitten" section, a bug log, its decision records). Read that first and start there. When it names none, these are the generic places to read first:

- **Paging cursors.** A keyset cursor that skips or repeats a row under concurrent writes; an offset fallback that crept in beside it.
- **Tenant, ownership and permission filters.** A query that bypasses the tenant filter (an `IgnoreQueryFilters`-style escape) and is not one of the deliberate, allow-listed cross-tenant reads, or a tenant id captured when the model is built instead of read per request.
- **The error catalog.** An error class with no message sentence, a `detail` that comes back null, a 4xx response with no machine-readable error key.
- **The transaction boundary.** A module context or use case opening its own connection or transaction, a mutating endpoint mapped outside the one mapper that wraps the unit of work, or a `throw` where the use case needs its counter or audit row kept (a "reject but keep" path).
- **Locale and right-to-left display at the edge.** A date through the platform's locale formatter instead of the project's formatter, a number not going through the project's number formatting, locale-specific text ordered in application code instead of in the database.
- **State transitions that skip their one owner.** A status set directly instead of through the single method that owns the transition and its side effects.
- **Boundary conditions, rounding and money.** Inclusive against exclusive bounds (`>` against `>=`), integer division, rounding mode, currency units.

## Prove

The proof is a **failing test that names the wrong behaviour**, written before the fix:

1. Write the test asserting the documented intent.
2. Run it. **It must fail**, and fail for the stated reason. Read the failure; do not assume it. A test that fails because of a typo in the test proves nothing.
3. Fix the cause. Not the symptom: if the wrong value arrives from two layers up, the fix is two layers up, even when a local guard would make the test green.
4. Run it again. It passes, and the whole suite still passes.

A candidate you cannot turn into a failing test is **not a finding** (except a stale doc, above). Report it as skipped with what you could not reproduce. That is honest and useful; a speculative fix is neither.

## Fix

- Fix the **cause**. A guard added at the symptom leaves the bug live for every other caller.
- If the cause is in another module, that is a STOP: write a handoff naming the `file:line` and the failing test you wrote, so the next session starts from evidence.
- Keep the diff to the bug. A drive-by rename in a bugfix hides the fix in the diff. The run's commits share one shipment.

## Verify

The project's full gate list, plus:

- The new test fails on the pre-fix code (paste both runs: red then green).
- The full suite passes with zero failures (the project's full command, or its frontend check for a frontend scope).
- No other test changed. A test you had to edit to make green means the behaviour change was wider than the bug: stop and explain it.

## Specific STOPs

Beyond the universal list:

- **The "bug" is a documented decision.** Read the scope's card first. Several things look wrong and are not (a deliberate cross-tenant read such as a market view that lists other tenants' rows, an identical answer given to avoid leaking whether an account exists, a counterparty's audit row attributed to a tenant the actor is not in because it commits with the actor's own row and a lone one would be the bug).
- **The doc is the stale one.** Fix a stale docstring, comment or glossary entry as its own finding and say so; a stale ADR or instruction file is a handoff. Do not change working code to match a sentence nobody updated.
- **The fix changes an error key or a route constant.** Ask first: the error class name is the wire key, and the route is every caller's and every test's contract.
- **The fix amends an ADR.** That is a design decision with a human in it.
- **The behaviour is wrong only under a race you cannot reproduce.** Report it; a fix with no failing test is a guess with a commit message.

## Summary

Per the budget block: shipped (PR and SHA, or branch and SHAs, with the red-then-green evidence), skipped (with what you could not reproduce), or nothing found.
