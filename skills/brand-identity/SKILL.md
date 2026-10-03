---
name: brand-identity
description: Use when a client or project needs a logo — a new logo, wordmark, brand mark, monogram, logo refresh, or favicon/app-icon set — including one-line briefs like "make me a logo for X", or when the logo portion of a branding effort needs concepts to present.
---

# Brand identity — logo design

## Overview

A logo delivery is a strategic recommendation, not a drawing. The three failures that make one amateur: a single concept, the literal cliché, and no positioning behind the decisions. This skill is the contract for what a finished logo delivery contains.

## When to use

- Any logo request: wordmark, symbol/mark, monogram, lockups, refresh, favicon/app-icon set.
- NOT for: color/type/imagery systems, full brand boards, banners, or AI-raster "logo images". This skill covers the logo only, and logo masters are hand-authored vectors.
- Pure production on an existing approved mark (favicon set, colorway, cleanup): skip to steps 7–9 with the approved mark in place of the recommendation. The board holds sections 6–9 only, the Concepts / Positioning / Cliché / Rationale gates do not apply, and the spec drops its positioning line.
- Refresh (an existing mark is supplied): after step 3, list what customers already recognize (silhouette, colors, type style, name treatment) and mark each keep / evolve / replace with a reason. Steps 4–5 diverge only on the evolve/replace items — evolution beats reset. The board shows old vs new side by side.

## Workflow

1. **Brief.** Answer the 9 brief questions ([reference.md](reference.md)). If the user is reachable, ask the ≤3 questions that most change the design (audience, personality, competitors); assume the rest plausibly (all of it if the user isn't reachable) and mark every guess `(assumed)`.
2. **Position.** One sentence: "For [audience], [name] is the [category] that [differentiator]." Every later rationale traces back to it.
3. **Scan the landscape.** Name the industry's visual defaults and 3–5 competitor marks (knowledge or a quick search). List this industry's clichés (map in reference.md). Decide conform vs differentiate, with a reason.
4. **Diverge.** Write 10+ idea one-liners before drawing anything. The first ones will be the literal ones — the name illustrated ("Dawnroast" → sun + cup). Those are the ideas every competitor also had; keep going past them. Group survivors into 2–3 named directions.
5. **Concepts.** Draft ≥3 concepts from ≥2 directions — each gets a name, a one-line idea, and a rough SVG sketch. Wordmark-first: add a symbol only if its idea survives one sentence without the name next to it.
6. **Recommend one**, with a rationale that cites the positioning sentence and the landscape call, plus one honest line on each runner-up.
7. **Build the recommended concept only.** Horizontal lockup, mark-only (if a mark exists), stacked where useful; full-color, single-color black, white/reverse. Masters are paths only — outline any font text (tested snippet in reference.md).
8. **Validate by rendering.** Rasterize at 16/32/48 px and full size, mono and reverse — then LOOK at the renders and fix what breaks. A legibility claim without an inspected render is not validation.
9. **Deliver.** One presentation board (self-contained HTML, section order in reference.md), the spec, organized `svg/` + `png/` files, and a name-collision flag if a quick search shows the name visibly taken.

## Quality gates

| Gate | Pass = |
|---|---|
| Concepts | ≥3 presented on the board, from ≥2 directions, each named + idea line |
| Positioning | sentence exists; recommendation cites it |
| Cliché | industry clichés listed; one appears only with a named twist |
| Refresh | equity inventory (keep/evolve/replace) precedes concepts; old vs new on the board |
| Paths only | the SVG check in reference.md comes back empty; any font used is freely licensed, license noted |
| Small size | 16 px render inspected and survives |
| Colorways | mono black + reverse white built and rendered |
| Spec | HEX + job per color, clearspace, minimum sizes, 3 don'ts |
| Rationale | one line per major decision, strategic — not only aesthetic |

## Common mistakes

- **"One direction executed fully."** Execution completeness doesn't replace concept work — the client chooses from presented options.
- **Shipping the literal idea.** Name-as-picture is the default trap; it survives only as a runner-up unless the landscape scan shows the space is empty.
- **Differentiation by accident.** "The swash ampersand is the distinctive element" — if the claim fits any competitor, it isn't differentiation.
- **Legibility asserted, never rendered.**
- **Building every concept fully.** Sketches for the board; full variants only for the recommendation.

## Pending decisions

- Scope (logo-only v1 vs full identity v2) is undecided; don't change it without the user's call. Any next version needs the research-first opening and the brand-name gate (never invent a brand name; present researched candidates and wait for the pick).
