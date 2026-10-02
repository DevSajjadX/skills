---
name: product-purchase-research
description: Use when the user wants a product recommendation, comparison, or shopping research for something physical to buy — coffee gear, hardware, electronics, cases — including "which should I get" questions, price checks, and availability checks. Not for supplements, vitamins, or other nutrition products (dosing and safety questions are out of scope).
---

# Product purchase research

Work in this order: show the profile → pin the constraints → apply
dealbreakers as filters → check every market → compute landed USD →
recommend.

## 0. The user's buying profile

The user's region, markets, stores and dealbreakers live in one file on
their machine, outside this skill so updates never touch it:
`${XDG_CONFIG_HOME:-~/.config}/product-purchase-research/profile.md`.
It is the only record of these facts.

- **Every run, first:** read the profile and show it as one compact
  block — region and destination, each market with its stores and
  shipping, store kinds, dealbreakers — plus the file path, so the user
  sees what this research is limited to and where to change it.
- **Any field still `(not set)`** (all of them on the first run, when
  the file doesn't exist yet): ask for every one in a single message —
  region and delivery destination, the markets they can buy from and
  how goods reach them (direct, or a forwarder with its fee basis), the
  stores or kinds of stores to check. Write the answers in the format
  below, creating the folder if needed. A question the user skips or
  can't answer is written as `unknown` (`any` for stores, `none` for
  dealbreakers), never left `(not set)`, so it is not asked again —
  except the delivery destination and the markets, which research
  needs: those stay `(not set)` and are asked on every run until
  answered.
- **Research waits only for** a delivery destination and at least one
  market. Any other gap is worked around: `any` stores means the
  market's main stores; an `unknown` shipping fee becomes a labelled
  estimate (section 4).
- **Changes anytime:** the user may edit the file by hand, or ask
  ("add <store> to <market>", "drop <market>", "lift the <brand> ban");
  a request like that is the go-ahead — update the file and show the
  new block. Facts you only infer (a new refusal, a forwarder rate you
  looked up) are proposed for the file and written only on the user's
  yes.
- **`confirmed:`** is the month the user last said they can buy from
  that market. Older than six months → ask them to reconfirm when you
  show the block; on their answer, update the market and set it to the
  current month.

```markdown
# Buying profile
Read by the product-purchase-research skill on every run. Edit freely.
A field reading `(not set)` is asked on the next run.

## Region
- Region: <country you live in>
- Delivery destination: <city, country>

## Markets
- <market> — stores: <store names, or "any">; shipping: <direct | forwarder, fee basis | unknown>; confirmed: <YYYY-MM>

## Store kinds
- <e.g. official brand stores, large marketplaces, second-hand listings — or "any">

## Dealbreakers
- <refused product or attribute — or "none">
```

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
- Check every candidate against the profile's dealbreakers (section 0).
- A newly refused attribute is a dealbreaker for the rest of the
  session. Propose adding it to the profile; write it only on the
  user's yes.

## 3. Only the profile's markets count

- Never recommend an option sold only outside the profile's markets
  (section 0).
- Check every market — at its listed stores, or stores of its listed
  kinds — for every serious candidate; never stop at the first one
  that has it.
- If a market looks changed since its `confirmed:` month (a store
  gone, shipping halted), ask rather than assume, then update it as in
  section 0.

## 4. Prices are landed USD prices

- Convert every quoted price to USD so options compare directly.
- Fetch every exchange rate live during the task, never from memory,
  and state the rate, its source and its fetch time next to each
  converted price. A rate-source rule in the user's standing
  instructions (e.g. for one currency) wins.
- Report the real landed cost delivered to the profile's destination:
  item price + shipping/forwarder fee + any import duty or tax not already in the
  forwarder's door-to-door rate — never the list price.
- A market whose shipping fee is `unknown`, or a duty nobody knows:
  show a clearly labelled estimate with its basis (e.g. $/kg × weight),
  never a bare number. A rate you look up is proposed for the profile
  (section 0).
- If shipping from a market to the destination is infeasible or
  unclear, flag it instead of presenting the option as buyable.

## Shape of every recommendation

- Open with the profile block (section 0), then the constraints you
  optimized for, so a mismatch is visible immediately.
- For each option: landed USD price per market it is actually
  available in, with shipping feasibility noted, and the stores checked
  per market so a missed market is easy to spot.
- For mixed-use asks, lead with the balanced pick.
