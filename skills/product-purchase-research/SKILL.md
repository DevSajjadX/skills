---
name: product-purchase-research
description: Use for any product recommendation, comparison, or shopping research for this user — coffee gear, hardware, electronics, cases, anything physical to buy — including "which should I get" questions, price checks, and availability checks.
---

# Product purchase research

Work in this order: pin the constraints → apply dealbreakers as
filters → check reachable channels → compute landed USD → recommend.

## 1. Fit to stated constraints, not top specs

- Optimize for the user's stated real-world use, never for the most
  premium or best-specced option. Example correction: a Pelican hard
  case was rejected as "overkill — I want to put it in my backpack";
  everyday-carry and size constraints are hard requirements.
- For mixed use, prefer the balanced option: good at both beats great
  at one use and cheap at the other (e.g. one grinder that handles
  both 16g V60 and 8g espresso well beats a V60-only star).

## 2. Dealbreakers are filters, not preferences

- Any attribute the user refuses (a material, a feature) eliminates the option entirely. Do not
  trade it off against other merits.
- Dealbreakers stay in force across turns and sessions until the user
  explicitly waives them.

## 3. Only reachable markets count (last confirmed 2026-08)

- The user's reachable markets come from their standing instructions.
  Never recommend an
  option available only outside these channels.
- Check availability in every reachable channel for every serious
  candidate, not just one of them.
- If channel availability looks like it may have changed since the
  date above, ask rather than assume.

## 4. Prices are landed USD prices

- Convert every quoted price to USD so options compare directly.
- Report the real landed cost — item price plus shipping/forwarder
  fees to the user's hands — never the list price.
- If shipping through a reachable channel is infeasible or unclear,
  flag it instead of presenting the option as buyable.

## Shape of every recommendation

- Open by restating the constraints and dealbreakers you optimized
  for, so a mismatch is visible immediately.
- For each option: landed USD price per channel it is actually
  available in (every reachable channel checked), with shipping feasibility
  noted.
- For mixed-use asks, lead with the balanced pick.
