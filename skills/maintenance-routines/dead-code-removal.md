# Routine: dead code removal

Shared rules (preconditions, scope, proof standard, gates, ship protocol, budget, STOPs, never-touch, owner table) are in [SKILL.md](SKILL.md). Read it first. This file adds only what is specific to unreachable code.

## The defect

Code that **nothing can reach**: no caller, no route, no registration, no test that exercises it for its own sake. Not code that is ugly (that is `logic-simplifier`), not code that is duplicated (`dup-unifier`), not a test that can never fail (`useless-test-pruner`), not code that is reachable but rarely taken. Unreachable.

## Discover

Use the project's own dead-code detector if it has one; its `AGENTS.md` or `CLAUDE.md` says which, and it is usually already part of the gate list, so a hit here is a hit the gate also sees. Installing a new detector is a new dependency, which is a STOP, so use what already ships. A detector run ad hoc through `uvx` or `uv run --with` that the project does not ship counts as a new detector: sweep by references (grep across code, config and tests) instead.

**Use the language's own unused-code analyzer.** Every common language ships one; run the strictest form the project already configures:

| Language | Analyzer to run |
| --- | --- |
| C# / .NET | the style analyzers through `dotnet format style <solution> --verify-no-changes`: IDE0051 (unused private member), IDE0052 (unread private member) and IDE0060 (unused parameter) surface there and often nowhere else, because msbuild does not report them even with `EnforceCodeStyleInBuild` |
| TypeScript / JavaScript | knip or ts-prune for unused exports, files and dependencies; the compiler's `noUnusedLocals` and `noUnusedParameters`; ESLint `no-unused-vars` |
| Python | vulture; ruff's `F401` (unused import), `F841` (unused local) and `ARG` rules |
| Go | `staticcheck` (`U1000`), `unused`, `go vet` |
| Rust | the compiler's `dead_code` and `unused_*` lints, `cargo udeps` for dependencies |
| Java / Kotlin | the IDE inspections or `-Xlint`, detekt `UnusedPrivateMember` |

For orphaned files and modules, a dependency-graph tool's orphan report (dependency-cruiser, madge, import-linter) is a second view. **Every hit from any of these is a candidate, never a finding**: an analyzer sees only static references, so the sweep below still has to prove it.

Beyond the tools, sweep by hand: a handler or endpoint not registered in its module's registration list, a public type with no reference, an error class with no thrower, a config key nothing reads, a component no route renders, a store slice nobody maps.

## Prove

A candidate becomes a finding only with an **empty reference sweep**:

```bash
grep -rn "<SymbolName>" <source dirs> <test dirs> <config dirs>
```

The sweep must come back empty **except** for the definition itself and the test that exists only to exercise it. Before deleting, check each of these, because each one makes a symbol reachable without a textual reference:

- **It is registered.** A route, handler, command or plugin listed in a registry, router, config file or decorator is live even if nothing else names it. Grep the module's registration file for the symbol (the endpoint-mapping function, the handler registry, the plugin list); a use case listed there is live.
- **It is a public API.** An export listed in a package's public surface (`__all__`, an index file, a published package) may be imported by other repos. That is a STOP, not a deletion.
- **It is an error class or code.** Its name may be a wire key a client branches on, and may appear in message catalogs. A class with no thrower today is a STOP, not a deletion.
- **It is reached through an interface**, so the implementation has no direct caller, including an interface in a module's published contracts project.
- **It is generated, or used by the generated client.** A type that looks orphaned in generated output (an API client, a schema file, a spec) is regenerated with the project's generator, never deleted.
- **It is loaded by reflection or by name.** A string lookup (`globals()[name]`, `getattr`, a config file naming a function, a scan for subclasses, a resource read by name) reaches symbols with no textual reference to the symbol itself. Grep for the string pieces too. Typical cases: an error catalog that scans for exception subclasses and reads message resources by name, and a scanning library (an outbox's handler discovery, a DI container's assembly scan, a plugin loader) that loads its types the same way.

## Fix

- Delete the code **and the tests that exist only to exercise it**, in the same commit. A test left behind for deleted code is the next session's ghost.
- Delete its translations and messages too: a message key nothing renders, an error sentence whose class is gone. A catalog test that fails because a sentence and its class disagree is the check doing its job, not an obstacle.
- One deletion per commit. A commit that removes four unrelated things cannot be reverted for one of them. The run's commits share one shipment.

## Verify

The project's full gate list, plus:

- The detector's hit is gone and no new one appeared.
- The build is clean with warnings treated as errors where the project builds that way (`-warnaserror`, `--strict`, `noEmitOnError`), and the full test suite passes with zero failures. A test that now fails is proof the code was **not** dead: revert and report it as a skipped candidate.

## Specific STOPs

Beyond the universal list, each of these is a STOP: skip the finding and write its handoff (§ Universal STOPs in SKILL.md):

- **An unused public member on a shared interface** (a module's published contracts). That is a contract change, not a deletion.
- **An error class with no thrower** is still a wire key a client may branch on. A class with no thrower today may still be in the message catalogs and in a client's branch.
- **A route or path constant that looks unused.** Tests reference routes through the constant, and clients branch on paths.
- **Code marked as deliberate, ledgered debt** (a `DEBT #N` comment or equivalent). Deleting it means retiring the debt, which is its own change.
- **A genuinely unregistered handler or endpoint.** Dead and a bug: it was meant to ship. Report it as a handoff; deleting it silently throws away the intent.

## Summary

Per the budget block: shipped (PR and SHA, or branch and SHAs), skipped (with the missing proof), or nothing found. For each shipped deletion, paste the reference sweep command and its full output (before the deletion: only the definition and its own test; after: empty) in the summary or the commit body. An empty pass is a good result: say so plainly.
