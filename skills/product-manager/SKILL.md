---
name: product-manager
description: Use when a product or project question blocks the work and needs a PM's answer ("should we build X", "is this in scope", "what's the MVP cut", "which of these first", "a user asked for Y, do we add it", "how do we know it worked", "act as the PM", "judge this product"), or when an implementation choice would change what users can do, see or are told; also to break a topic down into board items ("break down X for the board", "what should the next iteration hold") and to keep the project's board ("add this to the board", "promote this handoff", "board status", "mark it done"). Not for how to build something already decided (engineering), or for writing the project's product docs.
---

# product-manager

Does a PM's three jobs on this project: **judge** a product question, **break down** a topic into board items, and **keep the board**. Every job answers from the project's own decisions first, then from established product practice, with every claim labelled by where it came from. The project's documents outrank good ideas.

## Pick the job

| The ask | Job |
|---|---|
| A question or choice: build X?, in scope?, which first?, MVP cut, how will we know | **Judge** (below) |
| "Break down", "brainstorm", "what goes in the next iteration" for a topic | **Break down** (below) |
| Add, place, promote, status, done, new iteration, demo-step, anti-goal: anything that writes or reads the board | **Board**: read `board.md` and follow it |

- Not for how to build something already decided (engineering), and not for writing the project's product docs (PRODUCT.md, specs, ADRs): propose the change and hand it to their owner.
- The board job is the only one that writes, and only to the board (plus the handoff it promotes).
- Cite a doc (a rule, an anti-goal, product truth) as its path plus the quoted words, with no line number: counted line numbers come out wrong, and a quote can be checked. Code evidence keeps `file:line`, copied from `grep -n` output or the source handoff.

## Judge

1. **State the question as a decision.** Who is affected (an end user, staff, an admin, or the next agent or developer when the ask is about tooling), what problem, which options. If the request names only a solution, write the problem it is meant to solve.

2. **Read the project's product truth before judging.** Follow the project's instruction file (`AGENTS.md`, `CLAUDE.md`) to its product sources, else search for them: product spec (`PRODUCT.md`, `docs/product/`), owner decisions, roadmap and release or acceptance criteria, anti-goals (`DO_NOT_DO`, non-goals, out of scope), open questions, ADRs, the issue or board item, done and queued work. Grep them for the question's nouns. Where the project says which source wins, follow it; without a stated order, a later dated owner decision beats an earlier one (cite both). An ask that duplicates done or queued work is answered by pointing at it.

3. **Classify the answer. Exactly one fits:**

   | Found | Answer |
   |---|---|
   | A decided rule covers it | Apply it and cite it. Not reopened unless the user asks; then name who decides. An ask the rule or an ADR makes impossible is a change to that decision, not a feature: say so in Basis, naming who could change it; never design around it. |
   | An anti-goal or out-of-scope line covers it | Quote the line, say why it applies, stop. Never reshape the ask into a variant that slips past the line; if the user still wants it, overturning the line is theirs to state. |
   | An open question with a stated default | Use the default, labelled "default, open with <owner>". Never settle it yourself. |
   | An open question with no default, or a problem too vague to name a "Done when" | Don't pick an answer. Name the owner and what it blocks, build only what doesn't depend on it, and propose parking it where the project keeps undecided problems. |
   | Nothing covers it | Judge with `lenses.md`, labelled "judgment". If it sets scope, a user-facing rule, policy, cost or legal exposure, it is the owner's call: give your recommendation as a question for them. |

4. **Look for the job behind the ask.** A complaint or request is evidence of a problem, not a spec. Check whether an existing, allowed path already solves it (a thread, a status, a support route) before proposing a feature; such a path counts only when the docs name it, so cite it. When the job itself falls inside an anti-goal, say so and offer no other route to it.

5. **Answer in this shape:**
   - **Verdict:** one line.
   - **Basis:** decided / anti-goal / default open with <owner> / judgment, each with its citation or lens.
   - **Why:** at most three bullets.
   - **Build / don't build:** what changes and what explicitly stays out. A user-facing change names what the user sees and what the system enforces together, never a backend half and a frontend half. Each excluded piece says where it lives instead (another item, a waiting decision).
   - **Done when:** the project's own acceptance check or demo step if one applies; else one outcome measure (`lenses.md` § How will we know). Each line names something a user, staff member or failing check can see; never "works correctly", "is improved" or "more robust".
   - **For the owner:** the one question only they can answer, with your proposed default; exactly "none" when the basis is decided or an anti-goal, since who could change that rule is already in Basis.
   - **Record it:** only when the basis is judgment and the verdict is a "no" for a general reason: the anti-goal line to add so the ask isn't judged again. Name the project's board or decision-log command if its instruction file gives one, else the file and section. Propose it; the board's `anti-goal` job writes it on the owner's yes.

## Break down

Proposes items; writes nothing. The board job materializes them.

1. **Read the canon and the constraints:** `board.md`, the board's roadmap and anti-goals, and the product truth (Judge step 2). A candidate that hits an anti-goal is rejected by name, with the quote.
2. **Read the board state:** every iteration's demo and items, the inbox, everything under `done/`, and the open handoffs in `.claude/handoffs/`. A candidate that duplicates done or queued work is dropped or merged into it, never proposed fresh; one an open handoff already covers is proposed as `promote`, not `add-item`.
3. **Shape each candidate:** who feels it, what is wrong or missing (with code evidence if there is one), its kind, the **first** iteration whose demo needs it and why, and observable "Done when" lines. Too vague for a "Done when" line: an inbox note. A new iteration only with its demo script. A candidate no existing demo step needs goes to a later iteration or the inbox; never add a demo step to justify a placement. A demo step you do propose is a `demo-step` job in the list below.
4. **Answer in this shape, and nothing after it:**
   - Each item in priority order: kind, iteration and why, problem, "Done when".
   - Rejected candidates, each with the anti-goal it hit.
   - **Summary:** one line per item, `N. <title> (iN, kind)`.
   - **To put it on the board:** the exact board jobs in order (`new iteration <title>` first, then `add-item iN <title>`, `demo-step iN <step>`, `add <idea>`, `promote <handoff> iN`). Run them only when the user says so.

## Common mistakes

| Mistake | Fix |
|---|---|
| Answering from general PM sense without opening the project's docs | Judge step 2 comes first, every time; the docs routinely forbid the "obvious" feature. |
| A quote with no path, or a path with no quote | Every doc citation is both: `PRODUCT.md` "No other emails in v1". |
| Writing board files during a break-down | Break down proposes; the board job writes, when the user says so. |
| Refusing a board write because the project has no board | `board.md` § Which board: create the default one and say so. |
| Linking a promoted handoff instead of moving it | `board.md` § promote: `git mv` it to a brief, or a queue run builds it again. |
| Deciding an open question because the default looks reasonable | Use the default, label it, name the owner. |
| Treating one user's complaint as a requirement | Find the job (step 4); one voice is a signal, not demand. |
| Success measured as "the feature works" | Tie it to the project's acceptance path or a user outcome. |
| Picking the most useful-sounding option for a release | Anything on the release's acceptance path beats anything off it. |
| Commercial lenses (positioning, margin) on a mandated or public service | Use the public-sector lenses; the client or law sets scope. |

Further reading behind the lenses: `sources.md`.
