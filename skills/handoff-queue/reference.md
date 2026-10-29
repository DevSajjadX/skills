# handoff-queue reference

Detail for the steps in SKILL.md. Read the part a step points at, not all of it.

## Baseline (step 4)

Before the first item, gate the clean starting commit once in a throwaway worktree (`git worktree add --detach <tmp> <base>`, removed after). Run the project's own gates (the end-to-end gate included), record each gate's exit code in the state file. That is the **environmental baseline**.

- A gate red in the baseline and red the same way after an item is environmental: note it, keep going, list it under Machine in the report.
- Any other red is the item's until the same gate, run on the base, fails the same way.
- Without a baseline, one pre-existing red gate parks every item.

## State on disk (steps 4 and 6)

Keep these under `.claude/handoff-queue/<date>/` in the main checkout, for a handoff queue and a milestone queue alike (untracked, never committed: add `.claude/handoff-queue/` to `.git/info/exclude` in step 4, so item commits and a `git clean -fd` on revert never touch it), updated as you go, so a run killed midway still leaves a true report:

- `queue.md`: one line per handoff with its verdict (ready, built, parked, not reached), the baseline's exit codes, the keep-awake pid if you started one.
- `decisions.md`: one line per decision you took in place of asking (the line, the reading you built, the source that supports it).
- `found/`: handoff files written for Found, not fixed, kept here during the run so a resume or the final-tip gate never mistakes them for queue items.
- `wi-<iid>.md` and `wi-<iid>/`: a milestone worker's status file and evidence (night-run.md).
- `<item>/`: one folder per item with its screenshots.
- `report.md`: the final report, rewritten after every item.

**Resume** after a usage limit or crash: read `queue.md` first, then `git log` on the branch, and restart at the first item not marked built or parked. Never re-gate or redo a finished item.

## Decide, don't ask (step 5)

An acceptance line that is ambiguous gets built in the reading the item's own sources support (its plan, the product doc, the issue it links). Log it in `decisions.md`. A question no source answers parks the item, never the run.

## Fix rounds (step 5)

A failing acceptance line or gate gets fix, re-gate, re-check. Two failed rounds park the item: revert it and keep the output.

## Browser walk (step 5)

SKILL.md, Human QA, is the whole rule. Evidence goes under `<state folder>/<item>/`, which the git exclude below keeps out of every commit.

## Report additions (step 7)

- Headline first line: `<date>: <n> done, <n> parked, <n> not reached`. Within each section, red items come first.
- **Decisions I took for you**: one line each, from `decisions.md`.
- **Machine**: what broke in the environment and how it was handled, plus the baseline's red gates.
- Each parked item: its output and the last green check.
- **Found, not fixed**: write each as a handoff file (plan-handoff's format) and list its path. Write it into `found/` in the state folder, then move it to `.claude/handoffs/` after the last item commit, uncommitted. Never in an item's commit.
