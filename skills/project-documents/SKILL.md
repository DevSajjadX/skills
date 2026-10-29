---
name: project-documents
description: Use when you create, edit, move or delete ANY .md file (agent instruction file, README, glossary, architecture doc, principles, conventions, ADRs, debt ledger, handoffs, plans, skills), whenever a feature build starts or is about to be declared done ("feature done", "DoD", "manual test script", "is this done?"), and whenever you are deciding WHERE to write something down (a decision, a rule, a term, a debt, a plan). If your change touches markdown or produces knowledge worth persisting, this skill applies. Not for code-only changes that touch no .md file and claim nothing done, for the project's board files (the board skill owns those), or for writing a skill's craft (that is writing-skills).
---

# Project documents: one home per fact

Every durable fact in a project has exactly one owning document; everything else points
at it. This skill is the method. Before writing anything down, find the owner in the
project's doc map (below). Writing it anywhere else creates the drift that makes the next
session implement against a stale prose copy.

**Trust hierarchy: code > tests > docs.** Before implementing against any doc claim,
verify it against the cited path. **A statement without a pointer is a hint, not a
source.** When a doc contradicts the code, the code is truth: fix the doc (or flag it),
never copy the stale claim.

## 1. Find the project's doc map

1. **Read the instruction file** (`AGENTS.md`, `CLAUDE.md`, or whatever the project names)
   for a document map, routing table or "where things live" section. If it has one, that
   map is the owner list: use it, with the role rules in section 2 applied to the roles it
   names. If the project has its own documents skill, follow its map and use this skill's
   hygiene, Definition of Done and role rules for what it leaves open.
2. **No map? Draft one from the repo.** List every `.md` file and doc folder
   (`git ls-files '*.md'`), read each one's first screen, and assign each to a role from
   the table in section 2. Mark roles the
   repo has no file for as "none yet" instead of inventing a file.
3. **Propose, never impose.** Show the drafted map as a table (document, owns, update when)
   and ask for a yes before adding it to the instruction file (or creating one). Until then, use it as your
   working map and say it is a draft.
4. Where the repo has two owners for one fact, or a fact with no owner, report it as a
   finding; do not silently pick.

## 2. Role rules (what each kind of document owns)

Match each role to the project's real file. The rules below are the generic form; the
project's map supplies the paths.

| Role | Owns (and who writes it) | Update when |
| --- | --- | --- |
| Agent instruction file (`AGENTS.md`) | Agent contract: gates (literal commands), Always / Ask-first / Never, the routing table, the workflow table, and the agent-session rules (handoffs, parallel sessions) | A standing rule for agents changes. Pointers, not prose: detail lives in the owning doc. Each `CLAUDE.md` is the one line `@AGENTS.md` when the project keeps an `AGENTS.md`; never a second copy (a repo check should verify it) |
| Module or feature card (`<module>/AGENTS.md`) | One scope's agent card, stable facts only: what it is, where things are (areas, not files), its boundaries and contract surface, the ADRs that bind it, the rules a compiler will not catch, its gate. A rule both sides keep lives once, in the module card's shared section; the feature card links to it | That module's surface, boundary or binding ADR changes. Pointers to rule IDs, never restated rules, never a per-file walkthrough or a list of generated operations, and never a copy of the module README, which owns what the module is |
| Project `README.md` | For humans: what the project is, why, how to run it | Setup or run steps change. No agent rules here |
| Module `README.md` | What one module owns, exposes, and deliberately lacks | The module gains or loses a table, a contract type, or a deferred item ships |
| Product document | The product, kept in English: what it does, its workspace, and the owner's decisions (the design system has its own file) | A product decision is made or reversed. When an item builds a rule, its terms move to the glossary and its shape to the architecture doc in that change; the rule stays here as intent |
| Glossary (`CONTEXT.md`) | Domain glossary: canonical term plus `_Avoid_` synonyms | **Same change** that introduces, renames, or retires a domain term. A term that exists only in code is a term the next session re-invents differently |
| Architecture doc (`ARCHITECTURE.md`) | What exists and how the pieces fit; ends with "What we deliberately don't have yet" | A cross-cutting shape changes, or a deferred item ships (remove it from the "don't have yet" list in the same change). The decision itself goes in an ADR; this file narrates the current shape |
| Human-owned onboarding or program docs (contributor tiers, onboarding, review guides) | The human process: rates, tier checklists, onboarding, the mentor's review guide, the contributor's PR self-review | The owner changes a rate, a tier item, or the review process. Points at rule IDs; never a second copy of a rule |
| Human guide to the agent workflow | What each skill does, what a maintainer approves, how to set up live QA | A skill's front door, a maintainer duty, or a gate name changes. Explains the instruction file; never a second copy of a rule: link the rule ID |
| Principles / constitution | Non-negotiable principles with stable IDs; they override every rule file | A principle is appointed or corrected: **append** the next free ID; never renumber or reuse an ID |
| Conventions (`docs/conventions/*.md`) | Every code rule, with stable rule IDs (a prefix per area); a routing table and a version in the conventions README | A rule is appointed or corrected: follow the self-update protocol in that README (apply, persist, bump version). Replace superseded rules in place, keep the ID, never renumber |
| ADRs (`docs/adr/NNNN-*.md`) | Invariants an agent could **not** infer from code: not a history | A rule exists that is invisible to the compiler, analyzers, linters and the conventions. Use the project's ADR template; **under 45 lines**; numbers are append-only. A stale `file:line` inside an ADR is a bug |
| Debt ledger (`docs/tech-debts.md`) | Index only: `#N label path` per line | A `// DEBT #N:` comment is added or retired in code. The body of the debt lives **at the code**, never in the ledger; a repo check enforces parity (when none exists, propose one) |
| Roadmap and anti-goals | The ordered, customer-testable iterations, and the anti-goals that reject an item outright: **human-owned** | An iteration is reordered or an anti-goal is appointed. An agent proposes the change and waits; it does not appoint one mid-task |
| Work queue (board, tracker, `.pm/`) | Iterations (demo script, items), briefs, inbox notes, and their done state. **Written only by the board skill** | The board skill's jobs (add, place, add-item, promote, new iteration, done). Every other skill (plan-execute, the routines, QA) reaches the board through the board skill or not at all |
| Handoffs (`.claude/handoffs/YYYY-MM-DD-<slug>.md`) | Out-of-scope work nobody has picked up yet; written by plan-handoff | Per the handoff rule in the instruction file's agent-session section: one self-contained file per item, plan-handoff's template. The board skill's promote moves it into an iteration as a brief; a plan-drafted one is deleted when its work lands; a won't-do is deleted |
| Plans (`.claude/plans/*.md`) | Execution plans (plan-draft output): **local-only, gitignored**; no committed file links one | Status flips (`draft`, `approved`, `done`) happen in the main checkout, never inside a worktree (a gitignored file there evaporates) |
| Skills (`.claude/skills/<name>/SKILL.md` + `evals/evals.json`) | One skill's procedure, and the prompts that prove it triggers | The procedure changes. The description must carry a trigger **and** a skip clause, `name` must equal the directory, and evals need at least 2 entries (a repo structure check should enforce it; propose one when none exists). Use writing-skills for the craft |
| Skill-family shared contract (`.claude/skills/<family>-shared/contract.md`) | Behavior shared by a skill family: the one copy | A rule applies to more than one family member. It goes here and the members link it; a member that restates it has forked the contract (a repo check should verify the link exists) |
| Generated contract (API spec and generated client) | The generated contract: **never hand-edited** | Only via the project's generator command after the source change; commit spec and generated code in the same commit as the source. a CI check should fail on drift (propose one when none exists) |

## 3. Hygiene rules (any .md touch)

- **One home per fact.** Before writing, ask which file owns it. If two files would say
  the same thing, one of them gets a pointer instead.
- **Moving or deleting a doc:** grep the repo for its filename and fix every live pointer
  in the same change: the instruction file, ADRs, conventions, `.claude/` included. A link
  to a deleted file is how the next session reconstructs a stale world.
- **No prose restatements of code** anywhere: no API shapes, field lists, or flow steps
  retold in markdown. Pointers (`file:line`, test names) and intent only. Behavior belongs
  in tests, invariants in ADRs, rules in conventions.
- Docs render for humans too: readable sentences, no filler. Run the project's markdown
  formatter check as part of its gate (the local gate command in the instruction file), and
  let an editor hook format as you write if the project has one.

## 4. Definition of Done: before claiming anything is done

Work through every item. **Evidence means pasted command output (the tail), not an
assertion that it passed.** You are the only reviewer this work gets before the user.

1. **Gates**: run the project's gate command (named in the instruction file's gates
   section) and paste its summary. A gate you skipped or filtered (`| grep -v ...`) is not
   a passing gate: say what you excluded and why.
2. **Every acceptance criterion carries its proof**: the test name (`file: "test title"`)
   or `manual §N` with the reason automation can't judge it. Every feature ships with its
   test: a backend slice gets tests in the module's test project (happy path plus
   denial/validation); a web feature gets an end-to-end spec. Use the project's own test
   layout, and its repo check or architecture tests that enforce this.
3. **Manual QA script written**: a **Setup** line first (which user, seed state, env
   flags), then 5 to 10 numbered steps with exact expected results ("row shows status
   `sent`", not "check it works"). Only what automation can't judge: feel, copy, layout,
   RTL, i18n.
4. **Known limits named**: every deliberate cut gets a `// DEBT #N:` comment at the code
   and its `#N label path` line in the debt ledger. Silent debt is the one thing this
   checklist must never allow.
5. **Sibling docs current**: read the glossary file and compare its terms against the change (new, renamed or retired terms); the
   architecture doc's "don't have yet" list if a deferred item shipped; an ADR if a new
   invariant exists that code can't express.
6. **Module card current**: if the change altered what a module or feature owns, its
   contract surface, a binding ADR, or a rule a compiler cannot catch, the scope's
   `AGENTS.md` says so. A card that still describes the old surface is worse than no card:
   the next session trusts it.
7. **Handoffs filed**: anything out-of-scope goes to `.claude/handoffs/` per the
   instruction file's agent-session rules, each mentioned in your final response.

Then hand the manual QA script to the user. **Do not declare the feature done to the user yourself**:
done is the user reporting the manual script passed. A plan's `status: done` means the plan finished executing, not that the feature is accepted. Your closing line: gates green
(evidence above), every criterion proven, manual QA ready.

### When manual QA fails

Each failure becomes a handoff file, not an inline fix, unless trivial and on a line
you're already editing. The QA run stays a QA run.

## Where this fits

plan-draft's "Docs surface" task and logic-bugfixer's doc fixes route through this skill.
