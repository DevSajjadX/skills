---
status: open
date: 2026-10-29
target: orders-api
origin_plan: none (found during a pricing review)
plan:
---

# Handoff: the orders API must send totals in cents

## Context

Seen while reviewing how pricing reads order totals.

## Problem

- The orders API returns totals as decimal strings ("49.99"), so `shipping_cents` here gets the wrong type.

## Contract

- `GET /orders/<id>` returns `total_cents` as an integer.

## Acceptance

- [ ] `curl -s localhost:8080/orders/1 | jq .total_cents` → an integer
