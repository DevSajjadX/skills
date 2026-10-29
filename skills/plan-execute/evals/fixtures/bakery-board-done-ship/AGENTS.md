# Example Bakery agent contract

Tests: `uv run --with pytest pytest -q`. The product board lives in `.pm/`; only the board's own job writes it.

Ship: a branch reaches `main` only through `/ship`; no gate runs in CI, so a direct push would merge code whose gates did not run locally.
