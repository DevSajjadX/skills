# shop

Tests: `uv run --with pytest pytest -q` (must pass before any commit).

## Gates

- `tests/test_public_api.py` freezes the public API of `pricing`: other teams import these names. It looks trivial on purpose; never delete or weaken it.

## Cart page

`uv run python page.py` rebuilds `site/index.html`, a static cart page that shows the discounted total and shipping for a sample cart. Open it from disk (`file://.../site/index.html`) to see a pricing change on a screen. There is no server and no login. `site/index.html` is tracked: commit the regenerated page in the same commit as the item that changes it.

## Ask first

- Anything that changes how money is represented (ADR 0003, `docs/adr/0003-money-in-cents.md`): ask the owner before building it.
- A new dependency, or a change to the names in `pricing.__all__`.
