# checkout

Toy order-total library.

## Tests

    uv run --with pytest --with pytest-xdist --with pytest-randomly pytest -q

CI runs the same command on a 2-worker runner with random test order.

## Rules

- Prices are integer cents. Never use floats for money.
