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

> **Run with:** `sonnet` / `low` effort. Two small tasks and three standing ones.

## 1. Goal & scope

Reject a booking for a full pickup slot.

## 3. Implementation tasks

- [ ] Add `is_full` to `slots.py`
  - Files: `slots.py`
- [ ] Reject a full slot in the booking handler
  - Files: `booking.py` (new)
  - Change: call `is_full` and return "That slot is full, pick another"

### Phase Z. Standing

- [ ] **Z1. Simplify**: run the simplify or review skill over the changed code
- [ ] **Z2. Test coverage**: tests for the full-slot rejection and the shared capacity number
- [ ] **Z3. Docs surface**: update every doc the change touches or makes stale

## 4. Definition of done

- [ ] A customer who picks a full slot sees "That slot is full, pick another" and no order is created
- [ ] The booking check and the slot list read the same capacity number
