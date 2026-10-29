# shopcart

Toy checkout library for the example store.

## Tests

    uv run --with pytest pytest -q

CI runs the same command (`.ci/pipeline.yml`).

## Rules

- The totals cache is bounded: at most 32 carts are held at once. The checkout
  box has little memory, so the bound stays.
- Prices are integer cents. Never use floats for money.
