---
name: handoff-queue
description: Use when the user leaves a queue of handoffs, tasks, or a tracker milestone or board of work items to work through while they are away and can't answer ("work through the handoffs while I sleep", "clear the queue overnight", "work this milestone down tonight", "do these while I'm out, don't ask me", "do these without me", or /handoff-queue). Not for one item the user is present for (that is plan-draft then plan-execute, or plain work), for a timed poll (that is /loop), for issues outside the queue given, or for writing a handoff (that is plan-handoff).
category: Workflow
tags: [workflow, handoff, board]
argument-hint: "[milestone, board filter or handoff folder; default .claude/handoffs/ when it has open items, else the open milestone with the most ready items]"
allowed-tools: "*"
---

# handoff-queue

The user is away, so every question they would have answered becomes a decision you make or an item you park. The queue is a list of claims, not orders: a handoff can contradict the product, depend on another, belong to another repo, or already be fixed. You leave the repo with one verified commit per finished item, on a branch of its own, and a report the user can act on in two minutes.

## The owner's standing brief

Every item in the queue is already approved as product, unless a product rule contradicts it (Steps, 2). Take each item that is not blocked through plan, cold review, build, human QA and ship (or leave on its branch, see What stands in for the owner), without asking anyone: in parallel wherever the dependency graph allows in a milestone queue, in dependency order in a handoff queue. Keep questions for the morning. Never run two end-to-end runs at once. Do as much as the night allows; never stop early.

Anything below that conflicts with this brief is a bug in this file.

## Two kinds of queue

| | Handoff queue | Milestone or board queue |
|---|---|---|
| Items | files in `.claude/handoffs/` | work items in a tracker, with blockers |
| Pipeline | Steps below, serial, one branch | [night-run.md](night-run.md) sections 0 to 6 replace Steps 3 to 7: up to three workers, a worktree each, a merge queue, a decisions log, a morning report |
| Push, PR, merge | never | the standing brief authorizes pushing item branches and shipping through the project's ship command |

The brief, Never, Human QA, Parking, Common mistakes and Steps 1 and 2 apply to both. With no argument, use `.claude/handoffs/` when it has open items, otherwise the open milestone with the most ready items. State on disk lives under `.claude/handoff-queue/<date>/` in the main checkout for both kinds (see [reference.md](reference.md)).

## What stands in for the owner

- **Plan approval** is the cold plan-review APPROVE, recorded on the plan as `approved_by: handoff-queue (plan-review APPROVE, <date>)`.
- **Merge approval** (milestone queue only) is the item's Definition of Done, observed: every acceptance line holds (walked per Human QA), gates are green on the exact head, and the merge queue's end-to-end run passed. Then the project's own ship command merges it: one item, one MR or commit, so the items that wait on it build on `main`. A project with no ship command stops at READY-TO-SHIP on the item's pushed branch, with the SHA.
- **Decide, don't ask.** An ambiguous acceptance line: build the reading that matches the item's sources (its plan, PRD, decision issues), and log it in `decisions.md` and the commit or MR. A question no source answers: park the item (Parking), never the run.

## Never

- Ask the user a question, write a "should I...?", or wait for a person (no AskUserQuestion).
- Run two end-to-end runs at once. A milestone queue runs e2e only in its merge queue; a handoff queue is serial, so its runs never overlap.
- Push, open a PR or merge in a **handoff queue**. In a **milestone queue** push only item branches and merge only through the project's ship command.
- Close an item whose acceptance lines were not each seen holding (Human QA).
- Do ask-first work the item does not itself name: a new dependency, module, route-constant change or error-class rename, or an ADR the item does not cite.
- Build an item whose change lands where an ADR or the instruction file (AGENTS.md or CLAUDE.md) says ask first, unless the item cites the owner's approval for it: park it under Decide. A milestone work item is approved product, so one that names the ADR or change approves it; a handoff that only names it does not.
- Fix out-of-scope findings inline: each is a handoff (plan-handoff), listed in the report.
- Write the project's own board files (for example `.pm/`) when this run's queue lives in a tracker: use the tracker.
- Report green that a gate, the e2e run or the browser walk did not show. Claims (an agent's report, an issue body, a label) are not evidence; a measurement at the SHA is.

## Steps

1. **Read the rules before the queue.** The project's AGENTS.md or CLAUDE.md, and every product doc it names (PRODUCT.md, anti-goals, a board, ADRs). These outrank any handoff.

2. **Gate each handoff** in `.claude/handoffs/` (or the list the user gave). This list, recorded in `queue.md`, is the queue for the whole run: handoffs written later are not in it. Gate before touching code, using the frontmatter (plan-handoff's format):
   - `target:` names another repo (this repo's name is the one AGENTS.md or the remote gives it): not yours to build. List it under Not reached with its target.
   - Park it, unbuilt, when its contract contradicts a product rule or anti-goal, whatever the handoff or an approved plan says the user wants.
   - `status: planned` with a `plan:`: run that plan with plan-execute when the plan is approved; otherwise park it under Decide. Where plan-execute would pause or ask, revert the item and park it under Decide with its options.
   - Park it when it needs a decision only the owner can make (a new dependency, a schema or public API change, spend, a wording the user signs), when it lands under an ask-first rule (see Never), or a plan because it won't fit one verified pass.
   - Park it when it states a problem that doesn't reproduce on the current code.

   Parking is the answer here, not a gap: a contradiction is never resolved by building the handoff and noting it, and never by editing the product doc.

   A milestone queue continues with night-run.md section 0 instead of the steps below.

3. **Order what is left.** By the project's priority if the handoffs carry one, then by how many other handoffs each unblocks, then by name. A handoff that names another as a prerequisite goes after it, and if that prerequisite is parked or fails, the dependent stays unbuilt (list it under Not reached, never build on a missing prerequisite). Two that edit the same function go one after the other, the later one starting from the earlier one's commit.

4. **Branch once, then baseline.** Commit on the branch the user named; otherwise create `handoff-queue/<date>` from the current HEAD and commit there. Never commit on the default branch unless a project rule says to. Then gate the clean starting commit once and record the baseline, open the state files, exclude the state folder from git, and keep the machine awake (on macOS `caffeinate -ims`, no `-d`; elsewhere the platform's inhibitor such as `systemd-inhibit`; pid recorded, stopped at the end): see [reference.md](reference.md).

5. **Work each item, one at a time, in the checkout:**
   - Reproduce the stated problem first, if it states one, and keep the output.
   - Ambiguous line: decide, don't ask (see What stands in for the owner).
   - Make the contract's change and nothing beyond it. A defect you notice on the way goes in the report, not in this commit.
   - Run every Acceptance line exactly as written and compare with its expected output. Then the project's own gates, the end-to-end gate included (items are serial, so runs never overlap).
   - A gate red that the baseline also shows is environmental: note it and keep going. Anything else is the item's until the same gate, run on the base, fails the same way.
   - **Human QA**: walk the item per the Human QA section.
   - Any other red: fix, re-gate, re-check. Two failed rounds, or a red you can't fix within the contract: revert the item, park it with the output.
   - One commit per handoff, through the project's commit rules, with `git rm` of the handoff file in that commit: a missing handoff means done. Evidence and state files never go in it. A file the item's own command regenerates (a built page, a snapshot) is committed with the item when the project tracks it.

6. **Never push, merge, or open a PR** in a handoff queue, and never ask a question and wait. A local branch is the user's to keep or drop. Never stop early: no hour at which you give up. Bounded is scope (park the item), never effort. Keep the state files current so a crash or usage limit resumes from disk.

   When the queue is empty, run the project's full gates once on the final tip. A failure becomes a handoff under Found, not fixed. Only now move the found handoffs from the state folder into `.claude/handoffs/`, uncommitted.

7. **Leave the report**, in this order, as your final message (and kept current in the state folder). Open with a headline count (done, parked, not reached); within each section, red items first; details in [reference.md](reference.md):
   - **Decide**: one line per parked item that needs the user: the question, the rule or evidence it hit (`PRODUCT.md:4`, copied from `grep -n` output, never counted by eye), your proposed default.
   - **Done**: per item, the commit, each Acceptance command with its real output, the gate result, and the Human QA evidence or the line recording that no screen shows the effect.
   - **Decisions I took for you**: one line per ambiguous line you resolved, with the reading you built.
   - **Parked**: items parked for a failing gate or no repro, with the output and the last green check.
   - **Found, not fixed**: defects seen on the way, each with `file:line` and a handoff file written for it.
   - **Not reached**: other repos' handoffs with their target, anything left, and why (blocked by which item, or no slot before morning).
   - **Machine**: what broke in the environment, and the baseline's red gates.
   - **State**: read from commands run now, never from memory: `git status -sb` (branch, ahead of its remote) and `git remote -v`. Then: nothing pushed (a milestone run lists the branches it pushed and what it merged), no process left running (stop the keep-awake). Then send a push notification with the headline (the `PushNotification` tool, when the host offers it).

   A milestone queue uses night-run.md section 6's template, which keeps the same sections.

## Human QA

One rule: **every item walks the screen that shows its effect.** A backend-only item is not exempt: walk the screen that renders the change, or the staff screen that reads it. An item whose effect no screen reaches (a refactor, a constant no page renders, a project with no UI at all) records that line in the report, "no screen shows this effect", and uses the real output of its real interface (the acceptance commands) as the evidence. Never skip a walk because the item looks backend only without first looking for the screen.

Walk every acceptance line as a person would, in a real browser (when the host offers a browser pane, a new tab made with `tabs_create` and its tab id passed on every call, since other workers share the pane; a project's own browser driver otherwise). Start the item's own stack in the background from its worktree (milestone queue) or the checkout (handoff queue): the project's full-stack run command, with demo seed data on if it has one, or open the built page from disk when the project says so. Read the web origin from its output, never assume a port.

If the browser cannot open a `file://` page, serve its folder in the background (`uv run python -m http.server 0 --directory <dir>`, read the port from its output) and walk `http://127.0.0.1:<port>/<page>`. If no browser can reach the page at all, the item is not Done: list it under a "Walk blocked" line in the report with the reason and the page's generated text, and the headline counts it separately.

- Sign in through the screens, reading any code from the dev menu or equivalent. No login helper, `fetch`, `javascript_tool`, API call or browser-driver script to reach a state a person would reach by screens: click, type, read, wait.
- Walk every acceptance line, then the states around it: empty, denied, a reload, the alternate locale (when the product's default is another), right-to-left layout if the product supports it.
- **Evidence must be causally downstream.** Take a screenshot per acceptance line into `.claude/handoff-queue/<date>/<item>/`, then Read each one against its line. A login wall, a blank page or a screen a broken build would also show is a capture failure, not evidence. The assertion names a value only the change produces ("the price shows 12,000 after the edit"), never "the page rendered". Screenshots and state files never appear in a commit.
- A bug item is reproduced on a stack from the base branch first, so the before screenshot proves the bug existed.
- A line that does not hold: fix, re-gate, re-walk. Two rounds still failing: park the item.

## Parking

A parked item gets the tracker's blocked label (for example `glab issue update <iid> --label "<blocked label>"`) or, for a handoff, a Decide line with the file left open. One comment on the issue ("<date>: parked, <the question, the options, a recommendation>"), its branch kept (a milestone run pushes it for the morning; a handoff queue keeps it local), and a line in the report. Every item it blocks stays unready.

## Common mistakes

| Mistake | Fix |
|---|---|
| "The handoff asks for it, so the user wants it" | Step 2: a product doc outranks the handoff. Park it under Decide. |
| Building it anyway and flagging the conflict in the report | The commit is already in the user's history. Park instead. |
| Building a handoff whose `target:` is another repo | Step 2: list it under Not reached. |
| Committing on the default branch | Step 4: a branch of its own. |
| "Acceptance passes" without running it | Step 5: quote each command's real output. |
| Fixing a defect you found on the way | Step 5: report it under Found, not fixed. |
| A pre-existing red gate parks every item | Step 4: baseline first; a red the baseline shows is environmental. |
| Looping on a failing line | Step 5: two fix rounds, then park. |
| Building on top of a parked prerequisite | Step 3: the dependent stays unbuilt. |
| Stopping after the first park | Step 6: never stop early; park the item, keep the queue. |
| Pushing a handoff queue's branch so the user "sees it in the morning" | Step 6: local commits only. Only a milestone run pushes, and only item branches. |
| Asking the user, or waiting for an answer | Never: decide from the sources and log it, or park the item. |
| Two e2e runs at once | Only one e2e run at a time: the merge queue's in a milestone run, the serial item loop's in a handoff queue. |
| Skipping the walk because the item "looks backend only" | Human QA: find the screen that shows the effect first; skip only when none does, and say so. |
| Moving an item to Done with a "walk limit" note | Serve the page over http first; a walk that never happened is never green. |
| A screenshot of a login wall or blank page as evidence | Capture failure: the assertion names a value only the change produces. |
| Building an item that lands where an ADR or AGENTS.md says ask first | Park it under Decide unless the item cites the owner's approval. |
| Reporting green from an agent's say-so | Read the exit codes and evidence in its status file. |
| Screenshots or state files in an item commit | State lives in the excluded `.claude/handoff-queue/` folder; `git status` before every commit. |

## Arguments

$ARGUMENTS
