---
status: open
date: 2026-10-29
target: shop
origin_plan: none (found during a support call)
plan:
---

# Handoff: discount codes typed in lower case are ignored

## Problem

- `pricing.py`: `apply_discount(4000, "save10")` returns 4000. A customer who types the code in lower case gets no discount. The cart page (`site/index.html`, built by `page.py`) shows `Discounted: 40.00` for code `save10`.

## Contract

- `apply_discount` matches `SAVE10` case-insensitively; everything else unchanged. Backend only: do not edit `page.py` or `site/index.html` by hand.

## Acceptance

- [ ] `uv run python -c "from pricing import apply_discount as a; print(a(4000, 'save10'), a(4000, 'SAVE10'), a(4000, 'nope'))"` → `3600 3600 4000`
- [ ] `uv run --with pytest pytest -q` → all pass, including a test for a lower-case code
- [ ] `uv run python page.py`, then open `site/index.html` in a browser: the page shows `Discounted: 36.00`
