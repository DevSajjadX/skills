# Routine: duplicate unifier

Shared rules (preconditions, scope, proof standard, gates, ship protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to duplicated logic.

## The defect

**Two live copies of one business rule inside one module or one feature**, where a change to either is a bug unless both change. "One rule, one owner": everything else calls the owner.

This is about _rules_, not _shapes_. Two entry points that each build their own response record are not duplication. They are two entry points. Two places that each decide whether a customer may get a discount are one rule written twice, and the second one will drift.

## Discover

Look for the same **decision** in two places:

- Two entry points computing the same eligibility, price or status transition.
- A validator and a handler both enforcing the same rule (the handler's copy is the one that survives a validator refactor, and diverges).
- A rule enforced in backend code and re-enforced in a hand-written client schema (a zod schema, a form validator) that was supposed to derive from the generated one. Read the feature's card before calling this duplication: a hand-written restatement of a rule the generated schema already carries is the finding.
- The same query shape written twice with different filters.

Read the scope's `AGENTS.md` first. Several apparent duplicates are deliberate: a function that checks a similar condition on purpose (judged at a different moment, on different data), response shapes callers rely on separately, a form that renders its fields from a schema endpoint but never re-checks a value because one module owns every such rule, and reads that cross tenants on purpose where signed-in code relies on a tenant filter (a project usually keeps an allow-list test naming each, with its reason). Those are decisions, not drift.

## Prove

A candidate becomes a finding when **both** hold:

1. A test exercising the rule through **call site A** and a test through **call site B** both pass before the change. If one of them does not exist, write it first. That test is the proof, and it is what makes the unification safe.
2. Both tests still pass, unchanged, after both call sites route through the single owner.

If the two copies are **not** actually equivalent (one handles a case the other does not), that is not duplication. It is a behaviour difference, and unifying it silently changes behaviour. Report it as a candidate for `logic-bugfixer` and stop.

## Fix

- Put the rule in **one** place and have both call sites call it. Inside a module that means a domain method on the aggregate or a single private helper in the use case's own file, next to the code that owns the data, not a new `helpers/` or `shared/` folder and not a new abstraction layer.
- Name the owner after the **question it answers**, not the mechanism: `may_list_product`, not `check_product_stuff`.
- Do not move the rule to a shared package to unify two modules' copies. That is the cross-module STOP.
- Keep the commit to the unification. A rename, a reorder and a unification in one commit is three changes nobody can review. The run's commits share one shipment.

## Verify

The project's full gate list, plus:

- Both call-site tests pass, **unchanged from before the fix**. A test you had to edit to make green is not evidence of equivalence.
- Sabotage the single owner once and confirm **both** tests fail. If only one fails, the second call site is not actually routed through it. Restore the owner before committing.

## Specific STOPs

Beyond the universal list:

- **The two copies live in different modules.** Unifying them means a shared interface or package, a boundary design decision, not a cleanup. Write a handoff and leave both copies in place (naming the shared-interface or shared-package option, with its cost).
- **The copies are backend and frontend.** A rule mirrored across the two needs a parity test or a redesign where only one implementation exists, not a routine's judgement call.
- **One copy is generated.** Generated code is regenerated, never edited.
- **Unifying would change behaviour in an edge case** neither test pins. Pin it first or stop.

## Summary

Per the budget block: shipped (PR and SHA, or branch and SHAs), skipped (with the missing proof), or nothing found.
