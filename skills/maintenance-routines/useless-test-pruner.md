# Routine: useless test pruner

Shared rules (preconditions, scope, proof standard, gates, branch and commit protocol, budget, STOPs, never-touch, symptom table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to tests that cannot fail.

## The defect

A useless test stays green when the code it covers is wrong. It costs a run on every commit and, worse, it claims a behaviour is pinned when nothing holds it. Reading the test finds a suspect; **only sabotage proves one**.

Suspect shapes, each listed with the code it claims to cover:

- **Tautology:** asserts on a value the test built itself.
- **Over-mocked:** mocks the code under test, or every collaborator, so it checks its own wiring.
- **Not-null only:** proves the code ran, not that it was right.
- **Snapshot of everything:** any change just updates it.
- **Structure only:** checks what the type system already guarantees.

## Never prune

Read the project's rules on tests first (its `AGENTS.md` or `CLAUDE.md`, testing guide, gate scripts). These stay, however trivial they look; at most, repair them:

- A test the project names as a **gate**, a **coverage check** or an **architecture test**.
- A test an **ADR requires**.
- The **only test on a path**: deleting it leaves a behaviour with no test. It gets repaired, never removed.

## Prove by sabotage

For each suspect:

1. Break the covered behaviour for real: invert a condition, return a constant, skip a write. A compile error proves nothing.
2. Run that test. **Green under sabotage is a finding**; red means the test is good, so keep it and say so.
3. Restore the file exactly (`git checkout -- <file>`) before the next sabotage.

A tautology that touches no project code needs no sabotage: show that it imports or calls nothing it claims to cover.

## Fix with repair before delete

A useless test marks a behaviour someone meant to pin.

- Assert the real result and its failure case (`== 900`, and the no-discount case), not `is not None`.
- Call the real code; mock only the outermost I/O (mail, network, clock), then assert what the code sent it.
- Narrow a snapshot to the fields the behaviour owns.
- Delete only when another test that went red under the same sabotage already pins that behaviour, or the behaviour is not worth pinning; say which.
- Rerun the same sabotage on each repair: the repaired test must now go red. Restore, and it must pass. Keep both outputs.

## Verify

The project's full gate list, plus:

- `git status` and `git diff` show no sabotage left in source files. Check twice; a left-behind inverted condition is the worst outcome of this job.
- The test count moved by exactly what you deleted. A count that dropped further means a test went missing.

## Specific STOPs

Beyond the universal list:

- **The covered code is unreachable.** That is dead code ([dead-code-removal.md](dead-code-removal.md)); the test goes when the code goes.
- **The test fails sometimes.** That is flaky, not useless ([flaky-test-fixer.md](flaky-test-fixer.md)).
- **Sabotage turns the whole suite red**, so this test's verdict cannot be isolated: report it.
- **The only test on a path is the useless one and no real assertion can be written** (the behaviour needs a live service): report it, do not delete it.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| "I read it and it can't fail" | Sabotage it and show it staying green. |
| Deleting the only test on a path | Repair it; a behaviour with no test is worse than a weak one. |
| Keeping a not-null test because "it catches a missing return" | It stays green when the value is wrong; repair it to assert the value. |
| A repaired test never seen failing | Rerun the sabotage. |
| Sabotage left in the source | `git diff` on every file you touched. |

## Summary

Per the budget block: committed (branch, SHAs, with the red-then-green evidence per repair), skipped (with the missing proof), or nothing found. Report per test: verdict (good, repaired, deleted), the sabotage used, and red or green under it.
