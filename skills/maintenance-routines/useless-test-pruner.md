# Routine: useless test pruner

Shared rules (preconditions, scope, proof standard, gates, ship protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to tests that cannot fail.

## The defect

A useless test **stays green when the code it covers is wrong**. It costs a run on every commit and, worse, it reports coverage that does not exist, so the next session believes the behaviour is pinned when nothing holds it. Reading the test finds a suspect; **only sabotage proves one**.

Suspect shapes. When you list a suspect, name the code it claims to cover:

- **Tautology:** asserts on a value the test built itself.
- **Over-mocked:** every collaborator is a mock, or the code under test itself is, so the test asserts the mocks were called in the order the test wired them. It tests the wiring, not the behaviour.
- **Not-null only:** proves the code ran, not that it was right.
- **Snapshot of everything:** a snapshot so broad that any change updates it, so it never objects to anything; the update is reflexive.
- **Structure only:** asserts a DTO has three fields, or checks anything else the type system already guarantees.

## Preconditions specific to this routine

The shared preconditions apply. One more reason `git status` matters here: sabotage is undone with `git checkout -- <file>`, which would **wipe someone else's uncommitted edits in that file**. If any file you would sabotage carries uncommitted work you did not do, surface it and ask (an unattended run skips that file and writes a handoff). A cleanup must never sweep unrelated changes in either.

Read the project's rules on tests before listing suspects: its `AGENTS.md` or `CLAUDE.md`, testing guide and gate scripts.

## Never prune

These stay, however trivial or tautological they look (some are tautological on purpose); at most, repair them:

- A test the project names as a **gate**, a **coverage check** or an **architecture test**: a per-slice coverage assertion, a catalog test asserting that names match resources, a layering test.
- A test that a **repo check requires to exist**, such as a check demanding one end-to-end spec per feature folder. Deleting the spec fails the gate, and the gate is right. Find such checks in the project's check scripts, not only in its prose.
- A test that pins behaviour an **ADR requires**, even if it currently cannot fail. Repair it: that it cannot fail is the bug.
- The **only test on a path**: deleting it leaves a behaviour with no test. It gets repaired, never removed. A behaviour with no test is worse than a weak one.

## Prove by sabotage

**Sabotage is mandatory for every suspect, without exception.** Reading is how you find one; only a run proves it.

For each suspect:

1. Break the covered behaviour for real: invert a condition, return a constant, skip a write. A compile error proves nothing: a test that fails because the code no longer builds says nothing about the test. Never sabotage or edit generated code, applied migrations, lockfiles, env or secret files (see Never touch in [SKILL.md](SKILL.md)): it proves nothing, or regeneration masks the change.
2. Run that test and keep the pasted output. **Green under sabotage is a finding.** Red means the test is good: keep it, say so, and move on. That is a successful check, not a wasted one.
3. Restore the file exactly (`git checkout -- <file>`) before the next sabotage.

**A tautology is sabotaged too.** Sabotage the code its name or comments say it covers and show it stay green. That it imports or calls nothing is supporting evidence, not the proof, because reading is what this routine distrusts.

A test that names no covered code at all (`def test_x(): assert True`) has nothing to sabotage. Show from a run that it exercises no project code (for example a coverage run of that test alone that lists no project file), and it is deleted as a tautology. If it does touch project code but you cannot tell which, report it as skipped for that reason.

## Fix with repair before delete

A useless test marks a behaviour someone meant to pin. Deleting it throws away the intent along with the file.

- Assert the real result and its failure case (`== 900`, and the no-discount case), not `is not None`.
- Call the real code; mock only the outermost I/O (mail, network, clock), then assert what the code sent it. Before mocking a collaborator such as a database, check whether the project's test infrastructure already provides the real one (a database test container, an in-memory fake, a fixture). "It needs a database" is rarely a reason to mock.
- Narrow a snapshot to the fields the behaviour owns.
- Delete only when another test that went red under the same sabotage already pins that behaviour, or the behaviour is not worth pinning; say which, in the commit message and the report.
- Never leave a behaviour with no test because its only test was useless. That test gets repaired.

**Prove each repair.** Rerun the same sabotage: the repaired test must now go red. Restore, and it must pass. Keep both outputs.

## Verify

The project's full gate list, not only the tests (a repaired test can break lint, types or format; name any gate you skipped and why), plus:

- `git status` and `git diff` show no sabotage left in source files. Check twice; a left-behind inverted condition is the worst possible outcome of this job.
- The test count moved by exactly what you deleted and added. A count that dropped further means you broke test discovery, or a test went missing, not that you pruned well.
- The repaired test fails under sabotage and passes restored: both runs pasted.

## Specific STOPs

Beyond the universal list. **Hand off** (write to `.claude/handoffs/` through `plan-handoff` and name it in the report):

- **The covered code is unreachable.** That is dead code ([dead-code-removal.md](dead-code-removal.md)); the test travels with it.
- **The test fails sometimes.** That is flaky, not useless ([flaky-test-fixer.md](flaky-test-fixer.md)).
- **A repaired assertion fails against the current code.** The code has a bug ([logic-bugfixer.md](logic-bugfixer.md) owns it). Do not fix production code in this pass. Keep the original test unchanged (or add the repaired one marked a known failure per the project's rules) and put the repaired assertion in the handoff.

**Report as skipped** (no handoff needed: the finding is fully described in the summary):

- **Sabotage turns the whole suite red**, so this test's verdict cannot be isolated (a module every test imports, a shared fixture or config is the usual cause): report it as skipped, with the file restored exactly.
- **The only test on a path is the useless one and no real assertion can be written** (the behaviour needs a live service): report it, do not delete it.

**Anything else outside this defect class or this scope** (provably wrong code, duplicated or convoluted logic): note it in the summary and defer it to its row in the owner table in [SKILL.md](SKILL.md), never fix it here, and write no handoff for it.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| "I read it and it can't fail" | Sabotage it and show it staying green. |
| Skipping sabotage for a tautology | Sabotage the code it claims to cover; the run is the proof. |
| Deleting the only test on a path | Repair it; a behaviour with no test is worse than a weak one. |
| Keeping a not-null test because "it catches a missing return" | It stays green when the value is wrong; repair it to assert the value. |
| A repaired test never seen failing | Rerun the sabotage. |
| Sabotage left in the source | `git diff` on every file you touched. |
| Restoring with `git checkout` over someone's uncommitted edits | Check `git status` first; stop and ask. |
| Fixing the production code a repaired assertion exposed | Handoff with the assertion; keep the original test. |

## Summary

Per the budget block: shipped (PR and SHA, or branch and SHAs, with the red-then-green evidence per repair), skipped (with the missing proof), or nothing found. Report per test: verdict (good, repaired, deleted, skipped), the sabotage used, red or green under it, and for a repair the red-then-green outputs. A candidate you could not prove is skipped, stating which proof was missing.
