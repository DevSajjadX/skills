# The board

The board says **what** to build and **in which order**, as iterations a user can be shown. It never says **how**: that is the plan (plan-draft). This file is the canonical board format and the one place its conventions live (layout, item shape, templates); the break-down job reads it at runtime and never restates or diverges from it. The board job is the only writer of the board: break down proposes, the board job materializes, and the plan-execute step that finishes an item closes it by calling `done`, never by editing a board file.

Parse the job from the request; the default is `status`.

## Which board

1. **The instruction file (`AGENTS.md`, `CLAUDE.md`) names a board:**
   - A folder or a board command: use it, in its own format and through its own command. The rules below fill only what it leaves unsaid.
   - An external tracker (GitHub or GitLab issues, Jira, Azure Boards): the jobs map onto its own commands (task-summary for GitHub and Azure), and the `.pm/` folders below never apply. `add` and `add-item` create an issue; `promote` creates one from the handoff (Problem and Done when in the body, the Contract attached as design input), then stages `git rm` of the handoff and gives the issue link for the commit message; `done` closes it; `status` lists open ones; `place`, `new iteration` and `demo-step` map to the tracker's own milestone, iteration or label if it has one. Anything with no mapping, `anti-goal` included, is proposed to the owner instead.
2. **Else a `.pm/` folder exists:** use it.
3. **Else** search for an unnamed board the way Judge step 2 searches for product truth (`ROADMAP*`, `BACKLOG*`, `docs/roadmap`, a TODO list of planned work). Found one: ask which is the board before writing. None: on the first board write the user asks for, create the default board and say so:
   - `.pm/README.md`: what a reader of the repo needs: "Kept with the product-manager skill. `ROADMAP.md`: iterations in order. `iN/`: an iteration and its items. `inbox/`: problems not yet placed. `DO_NOT_DO.md`: anti-goals."
   - `.pm/ROADMAP.md`: an empty iteration table.
   - `.pm/DO_NOT_DO.md`: one line per file that already holds anti-goals or product rules, naming the file (and its heading, if it has one) and none of the rule's text, so the rule lives in one place; new board-level anti-goals are added below.
   - `.pm/inbox/`.

   Then propose the one line for the instruction file that names the board (`Work queue: .pm/`); its owner adds it.

Before any write, read the roadmap and every anti-goal source. An item that hits an anti-goal is **rejected by name**: quote it, say why, stop. Never reshape it into something that slips past.

If the project defines a board check (a lint, a script, a CI job), run it after every write and never report success while it fails. Without one, walk the self-check below yourself after every write and report each line you checked.

### Self-check (the rules below, as checks)

A project's machine gate is the copy of these. Any line failing means the write is not done:

- an item's `id:` matches its path, and done items live under a `done/` folder;
- every item has a valid `kind:`, a `## Problem`, and (in an iteration) a `## Done when`;
- no item carries a plan heading (`## Steps`, `## Files`, `## Tasks`, `## Implementation`, `## Approach`, `## Acceptance criteria`);
- every iteration has `## Demo script` and `## Items`, and its item checkboxes agree with the folders (`[x]` exactly for the items under `done/`);
- where the project keeps a flow catalog: every demo step cites a flow id that exists in it, and an iteration under `done/` cites only `built` flows;
- an iteration outside `done/` whose items are all `[x]` fails until it is moved to `done/iN/` (after its staging demo passes);
- the roadmap names every open iteration.

A status that disagrees with this check is worthless.

## Layout

| Path | Meaning |
|---|---|
| `ROADMAP.md` | the iterations in execution order, one row each: id, demo, status |
| `DO_NOT_DO.md` | anti-goals, or links to where they live |
| `iN/README.md` | an iteration: what the user can be shown, its demo script, its items |
| `iN/NNN.md` | an item: one feature, bug, task or debt; the problem, not the fix |
| `iN/BRIEF-<slug>.md` | design input for the planner (a promoted handoff); not an item |
| `inbox/NNN.md` | a problem not yet placed in an iteration |
| `iN/done/NNN.md` | a done item |
| `done/iN/` | a done iteration, with its items and briefs |

## Rules

- **An item states the problem, never the solution:** who hits it, what is wrong or missing, why it matters now, what becomes observable when it is solved, which product rules apply. No steps, files to touch, class or test names, estimates, or `## Steps`, `## Files`, `## Tasks`, `## Implementation`, `## Approach`, `## Acceptance criteria` sections. A `file:line` is allowed only as evidence that the problem exists.
- **"Done when" is observable:** each line names something a user, staff member or failing check can see; never "works correctly" or "is improved".
- **Name the problem:** an item or inbox title names the problem it answers, not the file it touches. Surface dependencies and risks between items. Prefer a rule that moves from prose into a gate over one restated in another document.
- **Kinds:** `feature` (the user gains something), `bug` (the product does the wrong thing), `task` (needed work with no product change: a deploy, a removal), `debt` (a structural risk that makes the product wrong or slow to change).
- **Placement:** an item goes in the **first iteration whose demo needs it**. A prerequisite belongs to the iteration that first depends on it, never earlier "because it's foundational". If an iteration's demo script cannot be walked without the item, the item belongs there.
- **End to end:** a feature's "Done when" names what the user sees **and** what the system enforces. One problem is one item, never a backend half and a frontend half: merge them. A structural gap with no screen of its own (a transaction rule, an outbox, a filter) is not its own item: it goes into the first feature item that needs it, as a paragraph of that item's Problem plus the observable "Done when" lines it adds. Only deploy and test tooling stands alone as an item (kind `task`).
- **Every iteration is demoable:** its `## Demo script` is numbered steps a user walks (on staging, or the project's demo environment), each observable. An iteration with no user-visible step is rejected as an anti-goal, even when the project has not written that line down.
- **Every demo step cites its flows** when the project keeps a catalog of flows or acceptance checks: a step ends with `[F-AREA-NN]` (several as `[F-AAA-01, F-BBB-02]`), each an id in the catalog (find it the way Judge step 2 finds product truth; the id format is the catalog's own, and its own status words map to `built`, `planned` and `retired`). A `retired` flow is no longer in the product: a demo step never cites one, and `status` flags a step that does. A step with no fitting flow gets a new `planned` row in the catalog in the same change. The board job never flips a row to `built`: the change that lands the flow's tagged end-to-end test does. An iteration whose steps cite a `planned` flow cannot move to `done/`.
- **The id is the item, the folder is its state:** `id:` is the path under `.pm/` without the extension and without any `done/` segment, so `i1/done/003.md` and `done/i1/done/003.md` both carry `id: i1/003`, and moving an item to done never rewrites its id. `place` is the one move that assigns a new id (`inbox/004` becomes `i2/007`); it says so and repoints every reference.
- **`status:` is `open` or `done`.** There is no third value. Work in flight is an open item on a branch.
- **Done work leaves the open tree:** a done item goes to `iN/done/NNN.md`; an iteration whose items are all done goes to `done/iN/`, and only once its demo script has passed on staging (the roadmap's own "when an iteration is done" rule, if it has one). Use `git mv`, so history follows.
- **Numbering:** scan the whole tree, every `done/` included, and take the next free zero-padded number in that folder. Never reuse one.
- **No secrets** and no real customer data in any board file: no credential, token, connection string or real company name, not even in a repro. A secret scanner that gates the push (gitleaks, Betterleaks) catches it too late: a leaked string outlives the topic.

## Jobs

The default is `status`. Every write job ends with `git status --short` showing exactly the files it meant to touch.

**Dry run, every write job.** On "show me first", "dry run", `--dry-run` or `DRY_RUN=1`, print the exact file operations the job would perform (each `git mv` source and target, each file created with its full text or the lines added, each id rewritten and reference repointed, each roadmap row) and mutate nothing. Stop there; run the job only on the user's go. The dry run still reads the roadmap and anti-goals, so it can reject by name.

- **`status`:** read the whole tree (every `.md` under the board), the roadmap and the anti-goals. Print the current iteration (the lowest open `iN`) with its open items, later iterations with open counts, the inbox, and open handoffs not yet on the board. Then flag: items against an anti-goal, items that describe a solution, "Done when" lines that aren't observable, demo steps no item covers. Writes nothing. Finish by running the project's board check and reporting its result. With none (a test gate is not a board check), say so, then walk the self-check above line by line.
- **`add <idea>`:** the next free `inbox/NNN.md` from the inbox template, the idea restated as a problem. An idea or title that arrives as a solution ("add a Redis cache", "one-click reorder", "add a shared form hook and migrate every form") gets one question: what goes wrong without it? File the answer as the problem, with no Steps or Files; when the problem is already clear from the idea, restate it and say you did.
- **`place <inbox/NNN> <iN>`:** `git mv` to the next free `iN/NNN.md`, rewrite `id:`, add `## Done when` if the note lacks it, add its line under the iteration's `## Items`, repoint every reference to the old id. Add the demo-script step the item makes observable, citing a flow (a new `planned` catalog row when none fits), and name that step in the report.
- **`add-item <iN> <title>`:** the next free `iN/NNN.md` from the item template and its `- [ ] iN/NNN · <title>` line under `## Items`. A title that names a solution is restated as the problem it solves, as in `add`. Add the demo-script step the item makes observable, as `place` does, and name it in the report.
- **`reword <iN/NNN> <section>`:** replace one line or one whole section of an **open** item (`## Problem`, `## Done when`, `## Rules` or `## Not in this item`) when a plan step, an owner decision or the built code changes what the item says. Keep `id:`, `kind:` and `status:`. Refuse a done item (its text is the record of what shipped), and refuse new text the rules above reject: a solution in place of the problem, a plan heading, an unobservable "Done when" line. Report the old and the new text.
- **`demo-step <iN> <step>`:** append a numbered, observable step to the iteration's `## Demo script`. Cite the flow it exercises (and add a `planned` catalog row when none fits, per the demo-step rule above). Only when the user asked for it, or the iteration's demo can't be walked without it; say which.
- **`anti-goal <line>`:** append it to `DO_NOT_DO.md` with its date and who decided it. Only on the owner's explicit yes (Judge's "Record it" proposes these).
- **`promote <handoff> <iN>`:** turns a `.claude/handoffs/` file into board work. Refuse, saying why, when it isn't in this repo's own `.claude/handoffs/`, its `target:` is another repo, its `status:` isn't `open` (a `planned` handoff is already in flight), or a plan lists it (`grep -rl <file name> .claude/plans`).
  Design input may also arrive as a commit: when the user names one (or the handoff cites it), the item's `## Design input` points at it as `git show <sha>:<path>`, never copied in.
  1. The handoff's **Problem**, with its code evidence, becomes the item's `## Problem`.
  2. Its **Acceptance** becomes `## Done when`, restated as what a person or a check observes.
  3. Its **Contract** is design: it stays in the brief, never in the item.
  4. `git mv` the handoff to `iN/BRIEF-<slug>.md` (the slug is its name without the date). Drop its `status:` and `plan:` lines and add `promoted: <date> to .pm/iN/NNN (was <old path>)`.
  5. The item's `## Design input` points at the brief; repoint every other reference to the old path. A promoted handoff no longer sits in `.claude/handoffs/`, so no queue run builds it twice. Moving it out of `.claude/handoffs/` and adding a `planned` flow row to the catalog (when a demo step needs one) are the only writes outside the board this job makes.
- **`new iteration <title>`:** create it from the iteration template: the next free `iN/README.md` and its `ROADMAP.md` row, in execution order. An iteration exists only when its demo script can already be written, and only when no existing iteration's demo can absorb the work. A new module, dependency, ADR or tool is raised as a question for the owner, never settled. Without a demo script from the user, propose one and wait for the go.
- **`done <iN/NNN>`:**
  1. Set `status: done` and `git mv` the item to `iN/done/NNN.md`. The `id:` does not change.
  2. Tick `- [x]` on its line in `iN/README.md`.
  3. If no open item remains and every flow the demo script cites is `built`, **ask** whether the demo script has passed on staging. A cited `planned` flow means the iteration is not done: name it and stop. Only on a yes, `git mv` the iteration to `done/iN/` and mark its roadmap row done. Without the yes, the board check stays red on purpose ("every item is done; move the iteration") until the demo passes.
  4. **Verify before returning:** the item exists only under `done/`, and the board check passes, or fails only on the pending iteration move you reported. Report the check's output.

## Templates

### Iteration `iN/README.md`

```markdown
# iN · <what the user gets, 2 to 4 words>

**Demo:** <one or two sentences: what the user does on staging at the end of this iteration>

## Demo script

1. <a step the user walks, with what they observe> [F-AREA-NN, when the project has a flow catalog]

## Items

- [ ] iN/NNN · <item title>
```

### Item `iN/NNN.md`

```markdown
---
id: iN/NNN
kind: feature | bug | task | debt
status: open
---

# <the problem: what is wrong or missing, not the fix>

## Problem

<who hits it, what happens today (code evidence as `file:line` if there is one), why it matters now, which demo step or later iteration depends on it>

## Done when

- <what a user, staff member or failing check can observe>

## Rules

- <product rules and decisions it must respect: path plus quoted words, not restatements>

## Not in this item

- <adjacent problems that belong to another item>

## Design input

- <BRIEF-<slug>.md, or a `git show <sha>:<path>` of earlier design; optional>
```

### Inbox note `inbox/NNN.md`

```markdown
---
id: inbox/NNN
kind: feature | bug | task | debt
status: open
---

# <one-line problem>

## Problem

<what is wrong or missing and why it matters. No plan.>
```
