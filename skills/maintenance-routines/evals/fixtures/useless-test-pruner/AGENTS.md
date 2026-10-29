# Tiny Shop (example project)

Made-up pricing and receipt code for a fake store. Amounts are integer cents.

## Test command

    uv run --with pytest pytest -q

Run it before and after every change. All tests must pass.

## Layout

- `shop/pricing.py`: discount math
- `shop/receipts.py`: builds a receipt and hands it to a mailer
- `tests/`: pytest suite

## Rules on tests

- `tests/test_architecture.py` is the project's coverage gate: every module in `shop/` must
  have a matching `tests/test_<module>.py`. It looks trivial. It stays; repair it at most.
- Mock only the outermost I/O (the mailer). Never mock the code under test.
