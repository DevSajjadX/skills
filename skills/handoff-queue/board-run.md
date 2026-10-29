# Board iteration run

The third queue kind: drain one iteration of the project's board, item by item, with the owner present or not. Items are claims already placed in an iteration, so the handoff gate (Steps 1 and 2 of SKILL.md) is replaced by the preconditions below. It composes skills and never reimplements them: product-manager (its board jobs) is the board's only writer, plan-draft and plan-execute own the work (plan-review is the cold review plan-draft runs), wrap's Ship section owns the path to the default branch. Ad-hoc implementation is never a step.

This kind overrides parts of SKILL.md: it does not open a `handoff-queue/<date>` branch, it lands on the default branch per the Ship section, and the Never line on pushing follows the Ship `push` key (below), not "never". Everything else in SKILL.md (Never, Human QA, Parking) still applies, with Decide and Parked meaning the same lines in the report, except: with the owner present, the Never line on asking does not apply (ask where this file says to); with the owner away, every ask becomes a Decide line in the report. It is a long sequential loop, not an interval poll (that is /loop). Items run one at a time.

## Arguments

An iteration id (`iN`). Empty: the **lowest open iteration** (the lowest `iN` folder of the board that is not under its `done/`), and say which one you chose. The board is whatever product-manager's board.md resolves (`.pm/` by default); `.pm/` below stands for it.

## Preconditions: verify once, up front

1. `git branch --show-current`. Work on the default branch in the main checkout, or on a short branch in a worktree that lands by `git merge --ff-only`. Do not stop only because the branch is not the default.
2. `git status`. Uncommitted work you did not do belongs to another session: surface it and ask before starting (owner present), or park the whole run with that line (owner away). Never sweep it into an item's commit.
3. `.pm/<iN>/README.md` exists. If not, stop and report.
4. Read the board's roadmap and its do-not-do list (`.pm/ROADMAP.md`, `.pm/DO_NOT_DO.md`) once. Every item you touch respects both.
5. The project's board check (its gate list says which) is green; with none, walk product-manager's board self-check (`board.md`) instead and say so. A board that already fails its own check is not a board you can trust to tell you what is done.
6. Owner away: open the state folder `.claude/handoff-queue/<date>/` in the main checkout (`queue.md`, `decisions.md`, `report.md`; see [reference.md](reference.md)), add `.claude/handoff-queue/` to `.git/info/exclude`, and keep the machine awake as SKILL.md Step 4 says (pid recorded, stopped at the end). Resume from `queue.md` and `git log` after a crash or usage limit.

## The loop

1. **Pick the next open item.** Read `.pm/<iN>/README.md`. Open items are the unchecked ones under `## Items`. Take the **lowest-numbered** open item that still has a live file (`.pm/<iN>/NNN.md`, not under `.pm/<iN>/done/`). Cross-check checkbox against folders; if they disagree, trust the item files, flag the drift and repair it through product-manager before continuing. Inbox notes (`.pm/inbox/NNN.md`) are not work for this loop: nobody placed them in an iteration. Leave them alone and list them in the final report. No open item: Exit. Announce the item and a one-line plan before doing anything.
2. **Branch.** At the start of a batch only: pull with rebase from the remote default branch if the owner has pushed elsewhere. Every item commits on the default branch (main checkout) or the short worktree branch, on top of the previous item's commit. One batch is at most one iteration (the project's batch ceiling rule, if its instruction file has one).
3. **Plan it.** If the item already has an approved plan under `.claude/plans/` (its `from_item:` is the item id, `status: approved`), reuse it and go to step 4; never draft a second one. Otherwise plan-draft `<iN>/<NNN>`: it loads the item, every brief its `## Design input` names and the iteration's demo script, and sets `from_item:` in the plan's frontmatter; it runs the cold plan-review. **Plan approval follows the project:**
   - The instruction file (AGENTS.md or CLAUDE.md) says plans need the owner's approval: an unapproved plan is **never self-approved**, whatever the review said. The item parks under Decide with the plan path and the question "approve this plan?"; the queue moves on to the next item. With the owner present, report the plan path and stop cleanly at that checkpoint instead.
   - The owner's explicit word in this session delegating approval ("approve the plans yourself") counts as owner approval, recorded as `approved_by: owner via chat (<date>)`.
   - Otherwise the run's own cold-review APPROVE stands in, recorded as `approved_by: handoff-queue (plan-review APPROVE, <date>)`.
4. **Execute it.** plan-execute `<plan path>`: it walks the task list, runs each task's gate, and calls product-manager's `done <iN>/<NNN>` once at close-out, when every line of the item's `## Done when` holds. You do not implement tasks yourself and you never write the board: one writer. plan-execute routes through product-manager (`done` at close-out, `reword` when a step changes an item's text). If the plan's close-out did not run `done`, run product-manager `done` for the item yourself; never edit a board file. Owner away: when `done` reaches its iteration question (demo script passed on staging?), answer nothing and leave the iteration open; list "iteration iN: demo ready to walk, move it?" under Decide. The plan's last tasks (simplify, test coverage, docs surface) are real work, not bookkeeping; their definitions live in plan-draft.
5. **Gate, then commit the item.** Before the commit, run the project's gate list in full (its instruction file's gates section) and paste the tails. A failing gate is a block, not a footnote: fix it before the commit. Never rewrite an earlier commit; a red found later is a new fix commit. Commit the item's code and its board move as **one** conventional commit that names the item (`feat(web): ... (i3/004)`), so a revert undoes exactly that item. Then back to step 1.
6. **Land per the Ship section.** Read wrap's Ship section settings (the project's instruction file):
   - `flow: direct`: each item lands on the default branch with wrap `m` (fast-forward only; from a worktree `git -C <main checkout> merge --ff-only <branch>`), gates before each commit, never a merge commit. Push only per the `push` key: `owner-word` (the default) leaves the whole batch committed locally and asks the owner whether to push, once; `allowed` pushes the batch once at the end. Every push to the default branch can start a pipeline on shared runners, so never push mid-batch.
   - `flow: pr`: each item ships through wrap `pr` (a pull or merge request); never `m` into the default branch. Merge only if the Ship section lets it and the run was told `--m`.
   - No Ship section: wrap's defaults apply and the report says which were assumed.

   Landing and pushing go through wrap, never raw git.

## Exit

- **Done**: no open item remains in the iteration. Report each item committed this run with its commit SHA, whether it is pushed, the inbox notes still waiting, and that **the iteration's demo script is ready to walk** (on the project's local full-stack run). **Never move the iteration** to `.pm/done/`: that needs the owner's yes through product-manager's `done` (the board's own "iteration done" step asks).
- **Blocked**: an item needs a decision only the user can make: ambiguous scope, an anti-goal conflict, an ask-first item (a new dependency, module, ADR, route-constant change or error-class rename, per SKILL.md Never), a `## Done when` line that cannot be observed from this repo, or a gate failure you cannot fix. Stop **before** committing half-work, report the exact blocker and what you need. Do not skip a blocked item to grab a later one unless the user says so. Owner away: the blocked item parks under Decide and the loop stops, since later items may depend on it; this overrides "never stop early" in SKILL.md Step 6. The one exception is an unapproved plan under an owner-approval rule (step 3): that parks the item under Decide and the queue moves on, because the plan, not the item, waits.
- **Checkpoint**: the user interrupts, or the run has gone long enough that a handover is warranted. Report committed, in flight and remaining so it resumes cleanly. When Blocked or Checkpoint stops the loop with committed items, the push question (step 6) fires there too, once.

## Guardrails

- **One commit per item; under `flow: direct` one push per batch.** The commit is the unit of rollback; the push is the unit of CI spend. Never mix two items in one commit, under `flow: direct` never push mid-batch, never push without the owner's word when `push` is `owner-word`. Under `flow: pr` each item branch is pushed once, for its PR.
- **Never leave red on the default branch.** Step 5 is the gate, before every commit.
- **product-manager owns the board.** An item is done when it sits under `.pm/<iN>/done/`, not when the code is written.
- **Ask-first stays ask-first.** A new dependency, module, ADR, tool-server config, route-constant change or error-class rename stops the item even mid-item. Autonomy is not authority.
- **Out-of-scope findings become handoffs** (plan-handoff), never an inline fix, never a board write.
- **Stay in `<iN>`.** This run is scoped to the iteration named.
- **Report honestly.** A skipped task, a mocked dependency, a flaky suite: say so in the per-item summary. Partial work presented as complete is the failure that compounds.
