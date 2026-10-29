# Pantry Co-op

Order and stock service for a made-up food co-op. All data is fake.

## Test command

```
uv run --with pytest pytest -q
```

Run it before and after every change. It must stay green.

## Layout

- `pantry/orders/` is the **orders** module: quotes, checkout, refunds, pricing rules.
- `pantry/stock/` is the **stock** module: shelf counts and case-pack math.

## Module boundaries

`orders` and `stock` are separate modules and never import each other. A function or type
that both modules need is a design decision for the maintainers, not a cleanup: write it up
under `.claude/handoffs/` and leave both copies in place until it is decided.

## Rules a test will not catch

- **Bulk discount.** A member order of at least 10 units with a subtotal of at least 50.00
  gets 5% off. One rule, used by both the quote preview and checkout. The constants live in
  `pantry/orders/pricing.py`.
- **Refund clawback is judged at purchase time.** `orders/refund.py` decides whether a
  partial return claws back the bulk discount. It checks `member_at_purchase`, not the
  customer's current membership, on purpose: a member whose membership lapsed after buying
  keeps the terms they bought under. It looks like the bulk-discount check. It is not the
  same rule.
- Each entry point (`quote`, `checkout`, `stock.report`) builds its own response dict.
  The callers rely on each shape separately; they are not meant to share one.
