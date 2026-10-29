---
name: useless-test-pruner
description: Use when asked to find, prune, clean up or fix tests that can't fail, assert nothing, or only test their own mocks ("prune useless tests", "these tests are pointless", "our coverage is fake", "slim the test suite"). Not for tests that fail sometimes (flaky), for missing coverage, or for tests of code being deleted (they go with their code).
---

# useless-test-pruner

A useless test stays green when the code it covers is wrong. It costs a run on every commit and, worse, it claims the behavior is pinned when nothing holds it. Reading the test is how you find a suspect; **only sabotage proves one**.

## Steps

0. **Precondition.** Run `git status`. Uncommitted work you did not make belongs to someone else: surface it and ask. Sabotage is restored with `git checkout -- <file>`, which would wipe their edits in that file, and a cleanup must never sweep unrelated changes in.

1. **Read the project's rules on tests first**: its AGENTS.md or CLAUDE.md, testing guide and gate scripts. A test the project names as a gate, coverage check or architecture test stays, however trivial it looks (some are tautological on purpose, such as a catalog that asserts names match resources); at most, repair it. The same holds for a test that pins behavior a decision record (ADR) requires: repair it, because that it can't fail is the bug.

   Work one scope (a module, a folder) per pass. With none given, survey, pick the single highest-value target and announce it with a one-line plan before any work. A finding that spans two scopes is a boundary question, not a bigger fix: stop and hand it off.

2. **List the suspects**, each with the code it claims to cover:
   - Tautology: asserts on a value the test built itself.
   - Over-mocked: mocks the code under test, or every collaborator, so it checks its own wiring.
   - Not-null only: proves the code ran, not that it was right.
   - Snapshot of everything: any change just updates it.
   - Structure only: checks what the type system already guarantees.

3. **Prove each one by sabotage.** For each suspect:
   - Break the covered behavior for real: invert a condition, return a constant, skip a write. A compile error proves nothing. Never sabotage or edit generated code, applied migrations, lockfiles, env or secret files: it proves nothing, or regeneration masks the change.
   - Run that test and keep the pasted output. Green under sabotage is a finding; red means the test is good, so keep it and say so.
   - Restore the file exactly (`git checkout -- <file>`) before the next sabotage.
   - A test that touches no project code at all (a tautology) needs no sabotage: show that it imports or calls nothing it claims to test.

4. **Repair before you delete.** A useless test marks a behavior someone meant to pin.
   - Assert the real result and its failure case (`== 900`, and the no-discount case), not `is not None`.
   - Call the real code; mock only the outermost I/O (mail, network, clock), then assert what the code sent it. Before mocking a collaborator such as a database, check whether the project's test infrastructure already provides the real one.
   - Narrow a snapshot to the fields the behavior owns.
   - Delete only when another test that went red under the same sabotage already pins that behavior, or the behavior isn't worth pinning; say which.
   - Never leave a behavior with no test because its only test was useless. That test gets repaired.

5. **Prove each repair.** Rerun the same sabotage: the repaired test must now go red. Restore, and it must pass. Keep both outputs.

6. **Verify and report.**
   - `git status` and `git diff` show no sabotage left in source files. Check twice; a left-behind inverted condition is the worst outcome of this job.
   - Run the project's full gate list (tests, lint, typecheck, format, repo checks), not only the tests: a repaired test can break lint or types. Name any gate you skipped and why.
   - The test count moved by exactly what you deleted.
   - Proof is pasted output, not a claim that something ran. A filtered gate (`| grep -v`) is a passing grep, not a passing check.
   - Report per test: verdict (good, repaired, deleted, skipped), the sabotage used, red or green under it, and for a repair the red-then-green outputs. A candidate you could not prove is skipped, stating which proof was missing.
   - An empty pass is a valid result: say "nothing found" plainly and never manufacture a finding to justify the run.

## Stop and hand back

**Hand off.** Write each to `.claude/handoffs/` with the `plan-handoff` skill and name it in the report:

- The covered code is unreachable: that's dead code, and the test goes when the code goes.
- The test fails sometimes: it's flaky, not useless.
- A repaired assertion fails against the current code: the code has a bug. Don't fix production code in this pass. Keep the original test unchanged (or add the repaired one marked a known failure per the project's rules) and put the repaired assertion in the handoff.
- Anything else outside this defect class or this scope (provably wrong code, duplicated or convoluted logic): note it and defer, never fix it here.

**Stop and ask or report.** These are not out-of-scope work, so no handoff:

- Sabotage turns the whole suite red, so this test's verdict can't be isolated: report it as skipped.
- A gate goes red and you can't find the root cause: stop and report.
- The repair needs a new dependency (new test infrastructure to replace mocks): ask first.
- The finding conflicts with the project's anti-goals or do-not-do list: ask.

## Common mistakes

| Mistake | Fix |
|---|---|
| "I read it and it can't fail" | Step 3: sabotage it and show it staying green. |
| Deleting the only test on a path | Step 4: repair it; a behavior with no test is worse than a weak one. |
| Keeping a not-null test because "it catches a missing return" | It stays green when the value is wrong; repair it to assert the value. |
| A repaired test never seen failing | Step 5: rerun the sabotage. |
| Sabotage left in the source | Step 6: `git diff` on every file you touched. |
| Restoring with `git checkout` over someone's uncommitted edits | Step 0: stop and ask first. |
