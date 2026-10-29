---
status: open # open -> planned (target /plan-draft consumed it); deleted (git rm) once the target plan's verification covers every Acceptance box, or when it won't be done (the commit message says why); moved into the board as a brief when promoted (or deleted, when the board is an external tracker, with the issue link in the commit message)
date: YYYY-MM-DD
target: <repo that must act: this repo's own name unless AGENTS.md declares a multi-repo workspace>
origin_plan: <absolute path to the plan that generated this handoff, or "none (found during <task>)">
plan: # set by the target repo's /plan-draft: path to the plan drafted from this handoff
---

<!--
A handoff is a PLANNING artifact for work found mid-task that is out of scope there:
another repo's change, or a find in this repo. It lives in the ORIGIN repo's
.claude/handoffs/ and replaces task chips, session cards and "want me to also...?" offers.
It must be self-contained: a fresh session with no memory of yours can run
/plan-draft <this path> in the target repo, or promote it onto the board. Keep it as
skimmable as a plan: short bullets, payload examples in fenced json, no prose walls.
-->

# Handoff: <one-line title>

## Context

<Which task surfaced this and why it was out of scope there; for a cross-repo need, why
the target repo is involved. Reference the origin plan path, do not restate its content.>

## Problem

<What is missing or wrong in the target repo. Evidence as `file:line` pointers, error text
verbatim, the failing command and its output. A claim without a pointer is a hint, not a
finding.>

## Contract

<The expected behavior or fix shape; for a cross-repo need, the API shape / event / schema the
origin side depends on. Endpoints, DTOs, error shapes, verbatim, with before/after payload examples if a contract changes. This
section is the whole point of the file: the receiving plan builds to exactly this.>

## Acceptance

<Each box is a command and the output that proves it, never "works correctly".>

- [ ] `<command>` → `<expected output>`
