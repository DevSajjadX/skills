# Shop

Tests: `uv run --with pytest pytest -q` (must pass before any commit). Commit after each change.

- `shop/__init__.py`'s `__all__` is the package's public API; two other repos import it.
- Event handlers register with `@handler("<event>")`; `config/events.json` maps events to them by name.
