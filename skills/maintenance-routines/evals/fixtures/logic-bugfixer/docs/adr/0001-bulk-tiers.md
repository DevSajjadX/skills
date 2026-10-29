# ADR-0001: Bulk discount tiers

Status: accepted

Bulk tiers are keyed on quantity with an **inclusive** lower bound:

| Quantity | Discount |
| -------- | -------- |
| 1-9      | 0%       |
| 10-49    | 5%       |
| 50+      | 12%      |

An order of exactly 10 units is in the 5% tier; exactly 50 is in the 12% tier.
