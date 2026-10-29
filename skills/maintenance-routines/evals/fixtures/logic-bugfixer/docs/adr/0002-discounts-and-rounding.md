# ADR-0002: One discount per quote, half-to-even rounding

Status: accepted

1. Discounts do not stack. When an order qualifies for both a bulk tier and the
   loyalty discount, the larger of the two applies. Finance asked for this so a
   loyal customer buying in bulk cannot reach a margin below cost.
2. The quote total is rounded once, half-to-even, to 2 decimal places. The
   fake ledger system downstream rounds the same way; rounding half-up here
   produced 1-cent mismatches in reconciliation.
