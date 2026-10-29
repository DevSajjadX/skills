---
status: open
date: 2026-10-29
target: shop
origin_plan: none (found during a support call)
plan:
---

# Handoff: tell customers when their order is refunded

## Problem

- A customer asked why they got no email after a refund.

## Contract

- `notify_paid` (or a new function) sends a "Refunded" email when an order's total goes negative.

## Acceptance

- [ ] `uv run --with pytest pytest -q` → all pass, including a refund-mail test
