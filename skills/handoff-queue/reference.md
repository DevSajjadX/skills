# handoff-queue reference

Detail for the steps in SKILL.md. Read the part a step points at, not all of it.

## Baseline (step 4)

Before the first item, gate the clean starting commit once in a throwaway worktree (`git worktree add --detach <tmp> <base>`, removed after). Run the project's own gates, record each gate's exit code in the state file. That is the **environmental baseline**.

- A gate red in the baseline and red the same way after an item is environmental: note it, keep going, list it under Machine in the report.
- Any other red is the item's until the same gate, run on the base, fails the same way.
- Without a baseline, one pre-existing red gate parks every item.

## State on disk (steps 4 and 6)

Keep these under `.claude/handoff-queue/<date>/` (untracked, never committed), updated as you go, so a run killed midway still leaves a true report:

- `queue.md`: one line per handoff with its verdict (ready, built, parked, not reached), the baseline's exit codes, the keep-awake pid if you started one.
- `decisions.md`: one line per decision you took in place of asking (the line, the reading you built, the source that supports it).
- `report.md`: the final report, rewritten after every item.

**Resume** after a usage limit or crash: read `queue.md` first, then `git log` on the branch, and restart at the first item not marked built or parked. Never re-gate or redo a finished item.

## Decide, don't ask (step 5)

An acceptance line that is ambiguous gets built in the reading the item's own sources support (its plan, the product doc, the issue it links). Log it in `decisions.md`. A question no source answers parks the item, never the run.

## Fix rounds (step 5)

A failing acceptance line or gate gets fix, re-gate, re-check. Two failed rounds park the item: revert it and keep the output.

## Browser walk (step 5)

When an acceptance line is observed in a UI (including a backend change whose effect shows on a screen), walk it in a real browser through the project's own driver, in a tab of your own.

- Click, type, read, wait. No `fetch`, injected script or direct API call to reach a state a person would reach through the screens.
- Read the origin from the stack's own output, never assume a port.
- Walk each acceptance line, then the states around it the project cares about (empty, denied, reload, another locale, RTL).
- **Evidence must be causally downstream.** One screenshot per acceptance line, saved under the state folder, then read back against its line. A login wall, a blank page or a screen a broken build would also show is a capture failure, not evidence. The assertion names a value only the change produces ("the price reads 12.00 after the edit"), never "the page rendered".
- A defect handoff is reproduced on the base first, so the before screenshot proves the bug existed.

## Report additions (step 7)

- Headline first line: `<date>: <n> done, <n> parked, <n> not reached`. A red item sits above a green one.
- **Decisions I took for you**: one line each, from `decisions.md`.
- **Machine**: what broke in the environment and how it was handled, plus the baseline's red gates.
- Each parked item: its output and the last green check.
- **Found, not fixed**: write each as a handoff file (plan-handoff's format) and list its path. Leave the file uncommitted, or in its own commit, never in an item's commit.
