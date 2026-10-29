# Routine: logic simplifier

Shared rules (preconditions, scope, proof standard, gates, branch and commit protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to behaviour-preserving simplification.

## The defect

Code that is **live, reachable, the only implementation, and harder to follow than the thing it does**. Nested conditionals that collapse to one guard clause, a loop that is a filter, a flag parameter that splits into two named functions, three variables tracking one state.

**Behaviour-preserving is the entire contract.** If the diff changes what the code does in any case, including an edge case nobody tests, it is not a simplification. It is a change, and it needs the owning module's judgement, not a routine's.

## Discover

Read, do not grep. Simplification candidates are found by reading a file end to end and noticing where you had to re-read a line. Signals worth trusting:

- A function whose name says one thing and whose body does three.
- A conditional whose branches all return the same shape with one field different.
- State carried in two variables that can never disagree.
- A `try/catch` that catches, logs and rethrows unchanged.
- Manual iteration where a comprehension, a filter or a single map says it plainly.

**Shortest correct diff, but correctness first.** Never simplify away validation at a trust boundary, error handling that prevents data loss, an authorization check, an accessibility attribute, or anything a project rule requires. Those are not complexity, they are the job. A check that looks duplicated may be the only one on another caller's path: find every caller before calling it redundant.

## Prove

The proof is a test that **pins the current behaviour before you touch anything**:

1. Find or write a test that exercises the code's behaviour, including its edge cases.
2. Run it against the **unchanged** code. It must pass. That run is the baseline.
3. Simplify.
4. Run the same test, **unedited**. It must still pass.

**If the behaviour cannot be pinned, STOP.** No test, no simplification. That rule is not bureaucracy: a simplification with no baseline is a rewrite with a reassuring commit message. Code whose behaviour depends on a live external service, with no recorded sample, cannot be pinned.

An untested edge case you discover while pinning is itself worth committing: that test is a finding, and it counts toward the budget as real work.

## Fix

- One simplification per commit, and its diff shows only it. A rename bundled with a restructure means the reviewer cannot see either.
- Follow the scope's existing shape; do not invent one.
- **Do not add an abstraction to simplify.** A new interface with one implementation, a new `shared/` folder, a new base class: each is more to understand, not less.
- Keep the comments that say **why**. Delete the ones that restate the code. A comment explaining a non-obvious decision is the most valuable line in the file.

## Verify

The project's full gate list, plus:

- The pinning test passes before and after, **unedited**.
- The full suite passes.
- `git diff --stat`: the change is smaller, or the same size and plainly clearer. A simplification that adds net lines needs a sentence explaining why.
- No public signature changed. If one did, this was an API change, not a simplification.

## Specific STOPs

Beyond the universal list:

- **The behaviour cannot be pinned with a test.** The single hardest STOP to respect and the one that matters most.
- **The code is convoluted because the domain is.** A five-branch state transition is five real states. Read the scope's card before deciding the code is worse than its subject.
- **The simplification is really a bug fix.** Hand it to `logic-bugfixer`, which will write the failing test first.
- **The candidate is a ledgered `DEBT #N` shortcut.** It is deliberate and has a stated upgrade path. Retiring it is its own change.
- **It spans two files in two modules.** Contract territory.

## Summary

Per the budget block: committed (branch, SHAs), skipped (with the behaviour you could not pin), or nothing found. An empty pass is a fine result. This routine has the highest risk of manufacturing work, so say "nothing found" without embarrassment.
