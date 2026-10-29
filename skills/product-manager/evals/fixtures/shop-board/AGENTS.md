# shop

Tests: `uv run --with pytest pytest -q` (must pass before any commit).

Product rules: `PRODUCT.md`. Work queue: `.pm/` (iterations, inbox, anti-goals in `.pm/DO_NOT_DO.md`).

## Gates

- `tests/test_public_api.py` freezes the public API of `pricing`: other teams import these names. It looks trivial on purpose; never delete or weaken it.
