---
status: open
date: 2026-10-29
target: shop
origin_plan: none (found during an accounting review)
plan:
---

# Handoff: represent prices as Decimal dollars

## Problem

- Accounting finds integer cents awkward when they read `pricing.py`.

## Contract

- `apply_discount` and `shipping_cents` take and return `Decimal` dollars (`Decimal("49.99")`) instead of integer cents.

## Acceptance

- [ ] `uv run python -c "from pricing import shipping_cents as s; print(s(__import__('decimal').Decimal('50')))"` → `0`
- [ ] `uv run --with pytest pytest -q` → all pass
