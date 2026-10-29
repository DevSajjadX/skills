# Example Bakery: Product

A web shop for one bakery. Customers order bread online and collect it in store. Owner: Dana.

## Product rules

- Orders are paid in store at pickup; there is no online payment in v1.
- A customer signs in with an email link.
- An order is for tomorrow or the day after, never the same day.
- After an order is placed, the customer gets one confirmation email. No other emails in v1.

## Out of scope in v1

- Delivery of any kind, subscriptions, gift cards.

## Acceptance flows

A flow counts as done only when its end-to-end test exists and passes.

| Id | Flow | Status |
|---|---|---|
| A-01 | A customer signs in and orders two loaves for tomorrow | tested |
| A-02 | A customer sees the confirmation with the right pickup weekday | tested |
| A-03 | Staff mark an order collected at the counter | planned, no test yet |

## Open questions

1. **Order changes** (Dana): can a customer change an order after placing it, and until when? No default yet; Dana is checking with the kitchen.
2. **Pickup window** (Dana): which hours can a customer collect? Default until Dana answers: 8:00 to 18:00.
