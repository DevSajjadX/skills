---
status: draft
execution_model: sonnet
execution_effort: low
adr: none
---

# Discount expiry Implementation Plan

> **Run with:** `sonnet` / `low` effort. Small, mechanical tasks.

**Goal:** SAVE10 stops working after 2026-12-31, paid-order mail reminds the buyer when their code expires within 7 days, and we measure discount throughput.

## 2. Assumptions and open questions

- Expiry date is fixed in code for now (owner confirmed).

## 3. Implementation tasks

### Task 1: Expire SAVE10

**Files:**
- Modify: `pricing.py:4-7`
- Test: `tests/test_pricing.py`

- [ ] Replace lines 4-7 with the version below, so the discount stops after `EXPIRES`:

```python
from datetime import date
EXPIRES = date(2026, 12, 31)

def apply_discount(total_cents, code):
    if code == "SAVE10" and date.today() <= EXPIRES:
        return total_cents - total_cents // 10
    return total_cents
```

- [ ] Add `test_save10_expired`, which patches `pricing.date` to return 2027-01-01 and asserts 1000 stays 1000.

### Task 2: Expiry reminder in the paid mail

**Files:**
- Modify: `notifier.py:1-3`
- Test: `tests/test_notifier.py`

- [ ] Give `notify_paid` a `today` parameter (default `date.today()`), and when the order has `code == "SAVE10"` and `EXPIRES - today <= 7 days`, send `"Paid. Your SAVE10 code expires soon"` instead of `"Paid"`. It computes the discounted total with `apply_discount` for the mail body.
- [ ] Add `test_reminder_near_expiry`, calling `notify_paid(order, mailer, today=date(2026, 12, 28))` and asserting the reminder text and the discounted total 900 in the body.

### Task 3: Measure discount throughput

**Files:**
- Create: `tests/test_pricing_perf.py`

- [ ] Time 1000 calls of `apply_discount`:

```python
import time
from pricing import apply_discount

def test_discount_throughput():
    t0 = time.perf_counter()
    for _ in range(1000):
        apply_discount(1000, "SAVE10")
    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    calls_per_ms = 1000 // elapsed_ms
    assert calls_per_ms > 0
```

## 4. Definition of done

- [ ] All tests pass. Verify: `uv run --with pytest pytest -q`

## 6. Skills Needed

None: plain Python.

## Execution log
