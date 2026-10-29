# Shop product rules

- Shipping is free from 50.00 (5000 cents); below that it costs 4.99.
- Customers get exactly one email per order: "Paid" when it is paid. No other emails in v1.
- Refunds are handled by staff by phone; the product sends nothing about them.
- Buyers see their orders on the "My orders" page; staff see every order in the back office.

## Flow catalog

| Flow | What the buyer or staff member does | Status |
|---|---|---|
| F-SHIP-01 | A buyer under 50.00 sees a 4.99 shipping fee at checkout | built |
| F-SHIP-02 | A buyer at 50.00 or more sees free shipping at checkout | built |
| F-ORD-01 | A buyer sees an order's status on "My orders" | planned |
