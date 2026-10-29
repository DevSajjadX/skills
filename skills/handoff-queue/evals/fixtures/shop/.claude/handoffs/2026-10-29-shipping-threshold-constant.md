---
status: open
date: 2026-10-29
target: shop
origin_plan: none (found during a README change)
plan:
---

# Handoff: name the free-shipping threshold and fee

## Context

Depends on `.claude/handoffs/2026-10-29-empty-cart-shipping.md` landing first: both edit `shipping_cents`.

## Contract

- `pricing.py` defines `FREE_SHIPPING_FROM_CENTS = 5000` and `SHIPPING_FEE_CENTS = 499`, and `shipping_cents` uses them. Behavior unchanged. `__all__` unchanged.

## Acceptance

- [ ] `grep -c "5000\|499" pricing.py` → `2` (only the two constants)
- [ ] `uv run --with pytest pytest -q` → all pass
