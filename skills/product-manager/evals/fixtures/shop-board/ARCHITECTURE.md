# Architecture

The shop is one Python package (`pricing`, `notifier`). Orders live in the orders service.

## What we deliberately don't have yet

- No order status history: only the current status is kept.
- No background job queue: see `docs/adr/0001-send-email-inline.md`.
