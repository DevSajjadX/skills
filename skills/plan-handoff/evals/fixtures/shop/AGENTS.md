# Shop

Tests: `uv run --with pytest pytest -q` (must pass before any commit).

## Gates

- `tests/test_public_api.py` freezes the public API of `pricing`: other teams import these names. It looks trivial on purpose; never delete or weaken it.

## Modules

`pricing` (money math), `notifier` (customer mail).
