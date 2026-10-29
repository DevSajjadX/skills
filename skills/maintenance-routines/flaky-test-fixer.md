# Routine: flaky test fixer

Shared rules (preconditions, proof standard, gates, ship protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to intermittent failures.

## The defect

A test whose result depends on something other than the code under test: execution order, shared state, wall-clock time, hash or iteration order, a real race, or a resource another session is using.

**A retry is never the fix.** A retried flaky test hides a real race that will surface in production instead of in a local run, and a suite with retries stops being evidence. This routine has one job: find the cause.

## Input

`$ARGUMENTS` is either a failing local run's log or a test name. The expensive suites (full browser end-to-end, database-container integration) often run only locally or before a release, and that is where flakes surface. With no argument, STOP and ask (an unattended run writes a handoff saying it was given nothing to reproduce, and ends). Hunting for flakes by re-running suites at random burns hours and finds the one that failed today, not the one that fails most.

Read the failure log before reproducing. The assertion that failed, and the values, usually name the category before a single local run.

## Reproduce: the proof standard

**Reproduce at least once in ten runs**, locally, before changing anything, with the project's own test command (repeat flags where the runner has them, otherwise a shell loop):

```bash
for i in $(seq 10); do <the project's test command> || echo "run $i failed"; done
```

Where the runner has a repeat flag, use it (`pnpm exec playwright test --repeat-each 10`, `pytest --count 10` with pytest-repeat, `go test -count 10`). For a suspect that depends on neighbours (for a backend, the whole solution or test project), run the whole suite rather than one test: order-dependence only shows when the neighbours run too. Also vary what the runner randomizes: hash seeds, test order, parallelism. Note the seed, the order and the machine state of the run that failed. That is the reproduction, and it is what proves the fix.

**Cannot reproduce in ten runs?** Do not fix. Report it: the failing log, what you tried, and what you would need. An unreproduced flake "fixed" by a plausible-looking change is a flake plus a diff.

## Categories, in the order worth checking

1. **Shared state.** A database, container, file or module-level global that one test leaves behind and the next asserts on. Fix: the test cleans up after itself, or asserts scoped to its own data, never by making it run first.
2. **Test ordering.** A test that passes alone and fails in the suite depends on a neighbour. Fix the dependency, not the order.
3. **Hash and iteration order.** Per-process hash randomization, unordered sets or maps, a bucket index derived from `hash()`. The same inputs collide in some runs and not others. Fix the code that derives behaviour from it.
4. **The clock.** Wall-clock time at a boundary (`DateTimeOffset.UtcNow`, `datetime.now()`, `Date.now()`), a token expiring mid-run, a date rolling over. Inject a fake clock through the seam the code already offers (a registered `TimeProvider`, a clock parameter, fake timers); a project that registers one did so precisely so tests can swap it, so use it.
5. **A real race.** Two requests on one row; a concurrency conflict that surfaces sometimes. This is not a test bug. It is a production bug the test caught. Fix the code, and say so loudly: a caught race is the most valuable finding this routine produces.
6. **UI timing.** A fixed sleep or wait-for-timeout, an assertion racing a re-render, a locator matching before the page is ready. Fix with an assertion that waits on the real condition, never a longer sleep.
7. **Port and parallel-session collisions.** Another agent session's stack, or a second run, on a fixed port or a shared database. Services should start through the project's launch configuration or its isolated-run command and never assume a port; the project's instruction file has a section on parallel sessions. If the test assumes a port, that is the bug.

## Fix

- Fix the **cause**, in the category you proved.
- **Never** add: a retry decorator or attribute, a longer timeout to paper over a race, a sleep, or a serialising lock, test collection or `--workers 1` that just hides the symptom.
- A retry that is **part of the product contract** (a client that documents a bounded retry on a transient error) is production behaviour, not a test retry. Leave it alone, and do not mistake it for the cause.
- If the cause is production code (category 3 or 5), it is a code fix with a test, and it must keep every documented constraint (a stated memory bound stays a bound). If it is outside this scope, it is a handoff with the reproduction attached.

## Verify

The project's full gate list, plus:

- The same ten-run loop that reproduced the failure now passes **ten out of ten**. Paste it.
- The full suite passes with zero failures on a full run, not only the one test.
- If the fix touched production code, a test pins the behaviour that was flaky.
- `git diff` contains no retry, no sleep, no widened timeout.

## Specific STOPs

Beyond the universal list, each of these is a STOP: skip the finding and write its handoff (§ Universal STOPs in SKILL.md):

- **Not reproducible in ten runs.** Report, do not fix.
- **It fails every time.** That is a bug, not a flake: `logic-bugfixer`.
- **The cause is the machine or its network**, not the test: a full disk, an image pull timeout, a rate limit. Report it; it is not a code change.
- **The fix would serialise a suite** that is parallel on purpose. That trades minutes per run for a hidden race, a decision with a human in it.

## Summary

Per the budget block: shipped (PR and SHA, or branch and SHA, with the before and after ten-run evidence and the category), skipped (with what you could not reproduce), or nothing found.
