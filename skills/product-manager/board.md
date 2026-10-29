# The board

The board says **what** to build and **in which order**, as iterations a user can be shown. It never says **how**: that is the plan (plan-draft). This file is the canonical board format; the break-down job reads it and never diverges from it.

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

If the project defines a board check (a lint, a script, a CI job), run it after every write and never report success while it fails. `status` runs it too and reports its result: a status that disagrees with the check is worthless.

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

- **An item states the problem, never the solution:** who hits it, what is wrong or missing, why it matters now, what becomes observable when it is solved, which product rules apply. No steps, files to touch, class or test names, estimates, or `## Steps`, `## Files`, `## Tasks`, `## Implementation`, `## Approach`, `## Acceptance criteria` sections. Code evidence that the problem exists is the one `file:line` an item carries.
- **"Done when" is observable:** each line names something a user, staff member or failing check can see; never "works correctly" or "is improved".
- **Kinds:** `feature` (the user gains something), `bug` (the product does the wrong thing), `task` (needed work with no product change: a deploy, a removal), `debt` (a structural risk that makes the product wrong or slow to change).
- **Placement:** an item goes in the **first iteration whose demo needs it**, never earlier "because it's foundational".
- **End to end:** a feature's "Done when" names what the user sees **and** what the system enforces. One problem is one item, never a backend half and a frontend half. A structural gap with no screen of its own is folded into the first feature item that needs it: a paragraph of that item's Problem plus the observable "Done when" lines it adds. Only deploy and test tooling stands alone as an item (kind `task`).
- **Every iteration is demoable:** its `## Demo script` is numbered steps a user walks, each observable. If the project keeps a catalog of flows or acceptance checks, each step cites it. An iteration whose demo script cites a flow or check that is not yet built and tested cannot be closed: `done` names the unbuilt flow and stops. A demo step with no fitting flow gets a new `planned` row, and only the change that lands the flow's test marks it built.
- **The id is the item, the folder is its state:** `id:` is the path under `.pm/` without the extension and without any `done/` segment. Only `place` changes an existing id; it says so and repoints references.
- **`status:` is `open` or `done`.** Work in flight is an open item on a branch.
- **Done work leaves the open tree:** `git mv`, so history follows.
- **Numbering:** scan the whole tree, every `done/` included, and take the next free zero-padded number in that folder. Never reuse one.
- **No secrets** and no real customer or company names in any board file, credentials not even in a repro.

## Jobs

The default is `status`. Every write job ends with `git status --short` showing exactly the files it meant to touch.

- **`status`:** the current iteration (the lowest open `iN`) with its open items, later iterations with open counts, the inbox, and open handoffs not yet on the board. Then flag: items against an anti-goal, items that describe a solution, "Done when" lines that aren't observable, demo steps no item covers. Writes nothing.
- **`add <idea>`:** the next free `inbox/NNN.md` from the inbox template, the idea restated as a problem. An idea or title that arrives as a solution ("one-click reorder", "add a shared form hook and migrate every form") is restated and filed as what goes wrong without it, with no Steps or Files.
- **`place <inbox/NNN> <iN>`:** `git mv` to the next free `iN/NNN.md`, rewrite `id:`, add `## Done when`, add its line under the iteration's `## Items`, repoint references.
- **`add-item <iN> <title>`:** the next free `iN/NNN.md` from the item template and its `- [ ] iN/NNN · <title>` line under `## Items`. A title that names a solution is restated as the problem it solves, as in `add`.
- **`demo-step <iN> <step>`:** append a numbered, observable step to the iteration's `## Demo script`. Only when the user asked for it, or the iteration's demo can't be walked without it; say which.
- **`anti-goal <line>`:** append it to `DO_NOT_DO.md` with its date and who decided it. Only on the owner's explicit yes (Judge's "Record it" proposes these).
- **`promote <handoff> <iN>`:** turns a `.claude/handoffs/` file into board work. Refuse, saying why, when it isn't in this repo's own `.claude/handoffs/`, its `target:` is another repo, its `status:` isn't `open` (a `planned` handoff is already in flight), or a plan lists it (`grep -rl <file name> .claude/plans`).
  1. The handoff's **Problem**, with its code evidence, becomes the item's `## Problem`.
  2. Its **Acceptance** becomes `## Done when`, restated as what a person or a check observes.
  3. Its **Contract** is design: it stays in the brief, never in the item.
  4. `git mv` the handoff to `iN/BRIEF-<slug>.md` (the slug is its name without the date). Drop its `status:` and `plan:` lines and add `promoted: <date> to .pm/iN/NNN (was <old path>)`.
  5. The item's `## Design input` points at the brief; repoint every other reference to the old path. A promoted handoff no longer sits in `.claude/handoffs/`, so no queue run builds it twice.
- **`new iteration <title>`:** the next free `iN/README.md` and its `ROADMAP.md` row, in execution order. An iteration exists only when its demo script can already be written.
- **`done <iN/NNN>`:** set `status: done`, `git mv` to `iN/done/NNN.md` (the id stays), tick its line, then verify the item now exists only under `iN/done/` (no stale open copy) and report the board check's result. When no open item remains, check the iteration's demo script cites no unbuilt flow (Rules, Every iteration is demoable), then ask whether the demo script has passed; only on a yes, `git mv` the iteration to `done/iN/` and mark its `ROADMAP.md` row done.

## Templates

### Iteration `iN/README.md`

```markdown
# iN · <what the user gets, 2 to 4 words>

**Demo:** <what the user does at the end of this iteration>

## Demo script

1. <a step the user walks, with what they observe>

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

<who hits it, what happens today (code evidence as `file:line` if there is one), why it matters now, naming which demo step or later iteration depends on it>

## Done when

- <what a user, staff member or failing check can observe>

## Rules

- <product rules and decisions it must respect: path plus quoted words, not restatements>

## Not in this item

- <adjacent problems that belong to another item>

## Design input

- <BRIEF-<slug>.md, optional>
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
