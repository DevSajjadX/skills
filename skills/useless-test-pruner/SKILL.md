---
name: useless-test-pruner
description: Use when asked to find, prune, clean up or fix tests that can't fail, assert nothing, or only test their own mocks ("prune useless tests", "these tests are pointless", "our coverage is fake", "slim the test suite"). Not for tests that fail sometimes (flaky), for missing coverage, or for tests of code being deleted (they go with their code).
---

# useless-test-pruner

A useless test stays green when the code it covers is wrong. It costs a run on every commit and, worse, it claims the behavior is pinned when nothing holds it. Reading the test is how you find a suspect; **only sabotage proves one**.

## Steps

1. **Read the project's rules on tests first**: its AGENTS.md or CLAUDE.md, testing guide and gate scripts. A test the project names as a gate, coverage check or architecture test stays, however trivial it looks; at most, repair it.

2. **List the suspects**, each with the code it claims to cover:
   - Tautology: asserts on a value the test built itself.
   - Over-mocked: mocks the code under test, or every collaborator, so it checks its own wiring.
   - Not-null only: proves the code ran, not that it was right.
   - Snapshot of everything: any change just updates it.
   - Structure only: checks what the type system already guarantees.

3. **Prove each one by sabotage.** For each suspect:
   - Break the covered behavior for real: invert a condition, return a constant, skip a write. A compile error proves nothing.
   - Run that test. Green under sabotage is a finding; red means the test is good, so keep it and say so.
   - Restore the file exactly (`git checkout -- <file>`) before the next sabotage.
   - A test that touches no project code at all (a tautology) needs no sabotage: show that it imports or calls nothing it claims to test.

4. **Repair before you delete.** A useless test marks a behavior someone meant to pin.
   - Assert the real result and its failure case (`== 900`, and the no-discount case), not `is not None`.
   - Call the real code; mock only the outermost I/O (mail, network, clock), then assert what the code sent it.
   - Narrow a snapshot to the fields the behavior owns.
   - Delete only when another test that went red under the same sabotage already pins that behavior, or the behavior isn't worth pinning; say which.
   - Never leave a behavior with no test because its only test was useless. That test gets repaired.

5. **Prove each repair.** Rerun the same sabotage: the repaired test must now go red. Restore, and it must pass. Keep both outputs.

6. **Verify and report.**
   - `git status` and `git diff` show no sabotage left in source files. Check twice; a left-behind inverted condition is the worst outcome of this job.
   - The full test command passes, and the test count moved by exactly what you deleted.
   - Report per test: verdict (good, repaired, deleted), the sabotage used, red or green under it, and for a repair the red-then-green outputs.

## Stop and hand back

- The covered code is unreachable: that's dead code, and the test goes when the code goes.
- The test fails sometimes: it's flaky, not useless.
- Sabotage turns the whole suite red, so this test's verdict can't be isolated: report it.

## Common mistakes

| Mistake | Fix |
|---|---|
| "I read it and it can't fail" | Step 3: sabotage it and show it staying green. |
| Deleting the only test on a path | Step 4: repair it; a behavior with no test is worse than a weak one. |
| Keeping a not-null test because "it catches a missing return" | It stays green when the value is wrong; repair it to assert the value. |
| A repaired test never seen failing | Step 5: rerun the sabotage. |
| Sabotage left in the source | Step 6: `git diff` on every file you touched. |
