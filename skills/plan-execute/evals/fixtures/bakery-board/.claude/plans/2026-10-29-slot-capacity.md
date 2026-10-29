---
status: approved
date: 2026-10-29
adr: none
skills: []
execution_model: sonnet
execution_effort: low
handoffs: []
from_item: i1/001
---

# Slot capacity

> **Run with:** `sonnet` / `low` effort. Two small tasks.

## 1. Goal & scope

Reject a booking for a full pickup slot.

## 3. Implementation tasks

- [ ] Add `is_full` to `slots.py`
  - Files: `slots.py`
- [ ] Reject a full slot in the booking handler
  - Files: `booking.py` (new)
  - Change: call `is_full` and return "That slot is full, pick another"

## 4. Definition of done

- [ ] A customer who picks a full slot sees "That slot is full, pick another" and no order is created
- [ ] The booking check and the slot list read the same capacity number
