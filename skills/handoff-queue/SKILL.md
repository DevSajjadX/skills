---
name: handoff-queue
description: Use when the user leaves a queue of handoffs or tasks to work through while they are away and can't answer ("work through the handoffs while I sleep", "clear the queue overnight", "do these while I'm out, don't ask me"). Not for a single task the user is present for (that is plan-draft or plain work), or for writing a handoff (that is plan-handoff).
---

# handoff-queue

The user is away, so every question they would have answered becomes a decision you make or an item you park. The queue is a list of claims, not orders: a handoff can contradict the product, depend on another, belong to another repo, or already be fixed. You leave the repo with one verified commit per finished item, on a branch of its own, and a report the user can act on in two minutes.

## Steps

1. **Read the rules before the queue.** The project's AGENTS.md or CLAUDE.md, and every product doc it names (PRODUCT.md, anti-goals, a board, ADRs). These outrank any handoff.

2. **Gate each handoff** in `.claude/handoffs/` (or the list the user gave) before touching code, using its frontmatter (plan-handoff's format):
   - `target:` names another repo (this repo's name is the one AGENTS.md or the remote gives it): not yours to build. List it under Not reached with its target.
   - Park it, unbuilt, when its contract contradicts a product rule or anti-goal, whatever the handoff or an approved plan says the user wants.
   - `status: planned` with a `plan:`: run that plan with plan-execute when the plan is approved; otherwise park it under Decide. Where plan-execute would pause or ask, revert the item and park it under Decide with its options.
   - Park it when it needs a decision only the owner can make (a new dependency, a schema or public API change, spend, a wording the user signs), or a plan because it won't fit one verified pass.
   - Park it when it states a problem that doesn't reproduce on the current code.

   Parking is the answer here, not a gap: a contradiction is never resolved by building the handoff and noting it, and never by editing the product doc.

3. **Order what is left.** By the project's priority if the handoffs carry one, then by how many other handoffs each unblocks, then by name. A handoff that names another as a prerequisite goes after it, and if that prerequisite is parked or fails, the dependent stays unbuilt (list it under Not reached, never build on a missing prerequisite). Two that edit the same function go one after the other, the later one starting from the earlier one's commit.

4. **Branch once, then baseline.** Commit on the branch the user named; otherwise create `handoff-queue/<date>` from the current HEAD and commit there. Never commit on the default branch unless a project rule says to. Then gate the clean starting commit once and record the baseline, open the state files, and keep the machine awake (`caffeinate -ims`, no `-d`, pid recorded; stop it at the end): see [reference.md](reference.md).

5. **Work each item, one at a time:**
   - Reproduce the stated problem first, if it states one, and keep the output.
   - Make the contract's change and nothing beyond it. A defect you notice on the way goes in the report, not in this commit.
   - Run every Acceptance line exactly as written and compare with its expected output. Then the project's own gates.
   - A gate red that the baseline also shows is environmental: note it and keep going.
   - If an Acceptance line is observed in a UI, walk it in a browser with causally downstream screenshots ([reference.md](reference.md)).
   - Any other red: fix, re-gate, re-check. Two failed rounds, or a red you can't fix within the contract: revert the item, park it with the output.
   - Ambiguous line: decide, don't ask. Build the reading the item's sources support and log it; a question no source answers parks the item.
   - One commit per handoff, through the project's commit rules, with `git rm` of the handoff file in that commit: a missing handoff means done.

6. **Never push, merge, or open a PR**, and never ask a question and wait. A local branch is the user's to keep or drop. Never stop early: no hour at which you give up. Bounded is scope (park the item), never effort. Keep the state files current so a crash or usage limit resumes from disk.

   When the queue is empty, run the project's full gates once on the final tip. A failure becomes a handoff under Found, not fixed.

7. **Leave the report**, in this order, as your final message (and kept current in the state folder). Open with a headline count (done, parked, not reached), red items first; details in [reference.md](reference.md):
   - **Decide**: one line per parked item that needs the user: the question, the rule or evidence it hit (`PRODUCT.md:4`), your proposed default.
   - **Done**: per item, the commit, each Acceptance command with its real output, the gate result.
   - **Decisions I took for you**: one line per ambiguous line you resolved, with the reading you built.
   - **Parked**: items parked for a failing gate or no repro, with the output and the last green check.
   - **Found, not fixed**: defects seen on the way, each with `file:line` and a handoff file written for it.
   - **Not reached**: other repos' handoffs with their target, anything left, and why.
   - **Machine**: what broke in the environment, and the baseline's red gates.
   - **State**: read from commands run now, never from memory: `git status -sb` (branch, ahead of its remote) and `git remote -v`. Then: nothing pushed, no process left running (stop the keep-awake). Then send a push notification with the headline if the project has one.

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
| Pushing so the user "sees it in the morning" | Step 6: local commits only. |
