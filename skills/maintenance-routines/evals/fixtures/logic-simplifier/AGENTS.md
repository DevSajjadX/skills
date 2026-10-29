# Tiny Shop (example project)

Made-up checkout code for a fake store. Amounts are integer cents.

## Test command

    uv run --with pytest pytest -q

Run it before and after every change. All tests must pass.

## Layout

- `shop/discounts.py`: discount codes applied at checkout
- `shop/loyalty.py`: loyalty discount, fetched from the vendor service
- `shop/checkout.py`: checkout entry point (form input arrives here)
- `tests/`: pytest suite
