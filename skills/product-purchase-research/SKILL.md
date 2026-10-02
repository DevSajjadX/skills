---
name: product-purchase-research
description: Use when the user wants a product recommendation, comparison, or shopping research for something physical to buy — coffee gear, hardware, electronics, cases — including "which should I get" questions, price checks, and availability checks.
---

# Product purchase research

Work in this order: pin the constraints → apply dealbreakers as
filters → check reachable channels → compute landed USD → recommend.

## 0. Where the user's buying facts live

- Reachable channels and standing dealbreakers come from the user's
  standing instructions (a "Buying" section in their global CLAUDE.md,
  or memory). Read them before researching.
- If none are recorded, ask once for both, and offer to save the answer
  there.

## 1. Fit to stated constraints, not top specs

- Optimize for the user's stated real-world use, never for the most
  premium or best-specced option. Example correction: a Pelican hard
  case was rejected as "overkill — I want to put it in my backpack";
  everyday-carry and size constraints are hard requirements.
- For mixed use, prefer the balanced option: good at both beats great
  at one use and cheap at the other (e.g. one grinder that handles
  both 16g V60 and 8g espresso well beats a V60-only star).

## 2. Dealbreakers are filters, not preferences

- Any attribute the user refuses (a material, a feature) eliminates the
  option entirely. Do not trade it off against other merits.
- Check every candidate against the standing dealbreakers from
  section 0.
- A newly refused attribute is a dealbreaker for the rest of the
  session. Propose adding it to the standing list; write it there only
  on the user's explicit yes.

## 3. Only reachable channels count

- Never recommend an option sold only outside the reachable channels
  from section 0.
- Check availability in every reachable channel for every serious
  candidate; never stop at the first channel that has it.
- If channel availability looks like it may have changed since the
  user last confirmed it, ask rather than assume.

## 4. Prices are landed USD prices

- Convert every quoted price to USD so options compare directly.
- Fetch every exchange rate live during the task, never from memory,
  and state the rate, its source and its fetch time next to each
  converted price. A rate-source rule in the user's standing
  instructions (e.g. for one currency) wins.
- Report the real landed cost delivered to the user: item price +
  shipping/forwarder fee + any import duty or tax not already in the
  forwarder's door-to-door rate — never the list price.
- If a channel's forwarder rate or duty isn't known, ask the user; if
  they can't say, show a clearly labelled estimate with its basis
  (e.g. $/kg × weight).
- If shipping through a reachable channel is infeasible or unclear,
  flag it instead of presenting the option as buyable.

## Shape of every recommendation

- Open by restating the constraints and dealbreakers you optimized
  for, so a mismatch is visible immediately.
- For each option: landed USD price per channel it is actually
  available in, with shipping feasibility noted, and the storefronts
  checked per channel so a missed channel is easy to spot.
- For mixed-use asks, lead with the balanced pick.
