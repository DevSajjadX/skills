# Shop (fixture)

- Tests: `uv run pytest`. Lint: `uv run ruff check .`
- `tests/test_public_api.py` is the project's coverage gate: every public function in `pricing.py` must be referenced there. Never delete it.
- Decision record ADR-0003: totals are always integer cents.
