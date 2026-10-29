# Milestone or board queue: the worker pipeline

Use this in place of SKILL.md Steps 3 to 7 (Steps 1 and 2, the brief, Never, Human QA and Parking still apply) when the queue is a tracker milestone or board of work items (WIs) with blockers. Examples use `glab`; use the project's tracker CLI. Every command below is a placeholder: take the real ones from the project's AGENTS.md, CLAUDE.md or package scripts, and if one does not exist, say so in the decisions log and use the closest real command.

Arguments: `[<milestone>]`, default the open milestone with the most ready items.

## 0. Set up, once

1. The machine must not sleep overnight; the display may. In the desktop app, check `keep_awake_while_working` (the `ccd_settings` `get_settings` tool, when the host offers it): on, it already holds idle sleep while the run works, start nothing. Off, or outside the app: `caffeinate -ims & echo $!` (no `-d`), the pid in `queue.md` for the morning report to stop.
2. Resolve the milestone (`glab api "projects/:id/milestones?state=active"`). Read every open issue in it with its links (`glab api "projects/:id/issues/<iid>/links"`) into `.claude/handoff-queue/<date>/queue.md` in the **main checkout**, excluded from git through `.git/info/exclude` as in reference.md: iid, title, labels, `is_blocked_by` iids and their states.
3. **Ready** = open, not in the planning state (a decision still open), and every blocking issue closed. Order the ready set by priority label, then by how many open items it blocks, then iid.
4. `git fetch origin`, then gate a clean `origin/main` once in a throwaway worktree (the worker gate list, plus the slow end-to-end gate; throwaway worktree, removed after). Record each gate's exit code in `queue.md` as the **environmental baseline**. A failure here is not an item's to fix; each worker compares against it.
5. Open the decisions log `.claude/handoff-queue/<date>/decisions.md` and the morning report, and keep both current: a run killed at 04:00 must still leave a true report.

## 1. Launch a worker per ready item, up to 3 at once

The cap is the machine: each worker builds the project, runs its containers and a full stack.

For each item, the orchestrator, not the worker, cuts the ground:

```bash
WT=<main checkout>/.claude/worktrees/hq-<iid>-<slug>
git worktree add -b handoff-queue/<iid>-<slug> "$WT" origin/main
cp <main checkout>/.env* "$WT"/ 2>/dev/null; (cd "$WT" && <install command>)
glab issue update <iid> --unlabel "<ready label>" --label "<in-progress label>"
```

(For example, a pnpm and GitLab project: `pnpm install`, `workflow::ready for dev`, `workflow::in dev`.) Then `Agent(name: "wi-<iid>", subagent_type: "general-purpose")`, no model override (a plan is architecture), all launches of a wave in one message. The prompt gives the worktree's **absolute** path, the issue number, this file's absolute path with "follow sections 2 and 3", and the current decisions log path. A worker writes its status to `.claude/handoff-queue/<date>/wi-<iid>.md` (absolute path), and the orchestrator reads that file, never the worker's hand-back prose alone.

## 2. Worker: plan and review

1. `glab issue view <iid> --comments` and every issue it links. The issue's acceptance lines are the Definition of Done; the plan must cover each one.
2. `/plan-draft` from the issue, with the plan written to the main checkout's `.claude/plans/`. At a fork the skill would stop on: decide from the sources and log it, or, if no source decides it, return `PARKED` with the question.
3. Its cold review (plan-draft's review phase) runs in a fresh subagent. REVISE: apply the findings, one more fresh review. A second REVISE: `PARKED` with the findings.
4. APPROVE: set `status: approved` and the `approved_by:` line. Report the files the plan touches.

The orchestrator holds an item's build while another in-flight item's plan touches the same files; it builds once that one merges (from fresh `origin/main`).

## 3. Worker: build, gate, walk

1. `/plan-execute <plan>`, narrowest check per task. A divergence the plan does not cover: decide and log, or `PARKED`.
2. One conventional commit for the item, `Closes #<iid>` in its body.
3. **Gate, without e2e**, since the merge queue owns e2e: `<gate command> --skip <e2e gate>` (for example `pnpm gates --skip e2e-critical`). A red gate that the baseline also shows is environmental: note it, move on. Anything else is the item's until the same gate, run on `origin/main`, fails the same way.
4. **Walk the Definition of Done as a person**: SKILL.md, Human QA. Evidence goes in `.claude/handoff-queue/<date>/wi-<iid>/` in the main checkout (absolute path), never in a commit.
5. Stop the stack, close the tab, set the in-QA-review label, write `READY-TO-SHIP` with the commit SHA, the gate exit codes and the evidence table to the status file, and return.

## 4. The merge queue: the orchestrator, one item at a time

The only place e2e runs, so no two e2e runs ever overlap (a run lock would queue a second one, and its timeouts under load read as failures). Take `READY-TO-SHIP` items in arrival order; for each:

1. `SendMessage` the worker: "your turn". It rebases on `origin/main` and runs all gates (the end-to-end gate included) plus every e2e spec its commit added or changed (`<e2e spec command> <spec>`, for example `pnpm --filter web test:e2e <spec>`). A rebase that pulled in other code but no conflict does not repeat the browser walk; a conflict does.
2. Green: ship it with the project's ship command (`Closes #<iid>` closes the issue when `main` moves). Red: back to section 3 with the output; the queue takes the next item.
3. Record the merged SHA. Recompute the ready set from the tracker (the merge may have unblocked items) and launch workers into any free slot (section 1).

## 5. Drive it: never idle, never stopped

- **Keep three slots full** while anything is ready. A slot frees when its item merges or parks.
- **Verify, don't trust.** Before an item enters the merge queue, read its diff and spot-check one screenshot. A worker's "green" is a claim until its exit codes and evidence are in its status file.
- **Broadcast corrections.** A defect one worker hits that others will (a gate tripping on load, a shared port, a seed missing) goes to every live worker by `SendMessage` at once, with a dated `CORRECTED` line in `decisions.md`.
- **Out of slots, out of ready items:** run the full e2e suite once on `main`; a failure becomes a handoff.
- **Usage limit or crash:** schedule a wake-up resume (`ScheduleWakeup`, when the host offers it); `queue.md` and the status files are the state, so a fresh orchestrator picks up from disk.
- **No hour at which it gives up.** The night ends when nothing is ready and nothing is in flight. Bounded is scope, never effort: park the item, keep the run.

## 6. Morning report

`.claude/handoff-queue/<date>/report.md` in the main checkout. Then one push notification (`PushNotification`, when the host offers it) with its title, and, if setup started a `caffeinate`, `kill <pid>` it so the machine may sleep again.

```markdown
# Night <date>, <milestone>: <n> merged, <n> parked, <n> not reached

## Decide (one line each: the decision, options, my recommendation, what it unblocks)

## Merged

| Item | MR | Merged SHA | Gates | e2e | Walked | Evidence |

## Parked: #<iid>, why, branch (pushed), last green check

## Decisions I took for you (one line each; full log: decisions.md)

## Found, not fixed: handoff paths

## Not reached: #<iid>: blocked by #<iid> / no slot before morning

## Machine: what broke and how it was fixed; the baseline's red gates
```

Plain sentences, a red item at the top beats a green one buried, every link real. SKILL.md's report order is the same report in handoff form; this template keeps the State lines (`git status -sb`, `git remote -v`, the branches pushed, what was merged) under Machine.
