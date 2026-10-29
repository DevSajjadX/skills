---
status: open
date: 2026-10-29
target: shop
origin_plan: none (found during a README change)
plan:
---

# Handoff: an empty cart is charged shipping

## Problem

- `pricing.py`: `shipping_cents(0)` returns 499. An empty cart has nothing to ship.

## Contract

- `shipping_cents(total)` returns 0 when `total <= 0`; everything else unchanged.

## Acceptance

- [ ] `uv run python -c "from pricing import shipping_cents as s; print(s(0), s(-5), s(4999), s(5000))"` → `0 0 499 0`
- [ ] `uv run --with pytest pytest -q` → all pass, including a test for a total of 0
