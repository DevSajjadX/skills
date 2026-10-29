promoted: 2026-10-20 to .pm/i1/001 (was .claude/handoffs/2026-10-18-slot-capacity.md)

# Slot capacity

## Contract

- Each slot holds 12 orders. The number lives in one config value, `SLOT_CAPACITY`.
- A full slot is rejected at booking time with the message above.
