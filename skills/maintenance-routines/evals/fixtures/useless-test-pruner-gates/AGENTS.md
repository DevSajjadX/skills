# Shop (fixture)

- Gates, all must pass: tests `uv run --with pytest pytest -q`, lint `uvx ruff check .`, repo check `uv run python scripts/check.py`.
- `tests/test_sync.py` is deselected from the default run (marker `sometimes_fails`); run it with `-m sometimes_fails`.
- `tests/test_public_api.py` is the project's coverage gate: every public function in `pricing.py` must be referenced there. Never delete it.
- Decision record ADR-0003: totals are always integer cents.
