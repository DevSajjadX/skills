# Routine: dead code removal

Shared rules (preconditions, scope, proof standard, gates, branch and commit protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to unreachable code.

## The defect

Code that **nothing can reach**: no caller, no route, no registration, no test that exercises it for its own sake. Not code that is ugly (that is `logic-simplifier`), not code that is duplicated (`dup-unifier`), not code that is reachable but rarely taken. Unreachable.

## Discover

Use the project's own dead-code detector if it has one: the linter's unused-symbol rules, a tool such as knip or vulture, the compiler's unused warnings. The project's AGENTS.md or CLAUDE.md says which. Installing a new detector is a new dependency, which is a STOP, so use what already ships. Beyond that, sweep by hand: a handler not registered anywhere, a public type with no reference, an error class with no thrower, a config key nothing reads.

## Prove

A candidate becomes a finding only with an **empty reference sweep**:

```bash
grep -rn "<SymbolName>" <source dirs> <test dirs> <config dirs>
```

The sweep must come back empty **except** for the definition itself and the test that exists only to exercise it. Before deleting, check each of these, because each one makes a symbol reachable without a textual reference:

- **It is registered.** A route, handler, command or plugin listed in a registry, router, config file or decorator is live even if nothing else names it.
- **It is a public API.** An export listed in a package's public surface (`__all__`, an index file, a published package) may be imported by other repos. That is a STOP, not a deletion.
- **It is an error class or code.** Its name may be a wire key a client branches on, and may appear in message catalogs.
- **It is reached through an interface**, so the implementation has no direct caller.
- **It is generated.** A type that looks orphaned in generated output is regenerated, never deleted.
- **It is loaded by reflection or by name.** A string lookup (`globals()[name]`, `getattr`, a config file naming a function, a scan for subclasses, a resource read by name) reaches symbols with no textual reference to the symbol itself. Grep for the string pieces too.

## Fix

- Delete the code **and the tests that exist only to exercise it**, in the same commit. A test left behind for deleted code is the next session's ghost.
- Delete its translations and messages too: a message key nothing renders, an error sentence whose class is gone. A catalog test that fails because a sentence and its class disagree is the check doing its job, not an obstacle.
- One deletion per commit. A commit that removes four unrelated things cannot be reverted for one of them.

## Verify

The project's full gate list, plus:

- The detector's hit is gone and no new one appeared.
- The build is clean and the full test suite passes. A test that now fails is proof the code was **not** dead: revert and report it as a skipped candidate.

## Specific STOPs

Beyond the universal list:

- **An unused member on a cross-module interface or a public export.** That is a contract change.
- **An error class with no thrower.** Its name is a wire key a client may branch on.
- **A route or path constant that looks unused.** Tests reference it and clients branch on it.
- **Code marked as ledgered debt** (`DEBT #N`). Deleting it means retiring the debt, which is its own change.
- **A handler or slice that is genuinely unregistered.** Dead and a bug: it was meant to ship. Report it as a handoff; deleting it silently throws away the intent.

## Summary

Per the budget block: committed (branch, SHAs), skipped (with the missing proof), or nothing found.
