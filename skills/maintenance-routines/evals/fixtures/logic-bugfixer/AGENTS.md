# Acme Widgets pricing (demo)

Test command: `uv run --with pytest pytest -q`

## Rules a compiler will not catch

- Discounts never stack. A quote applies the single best discount the order
  qualifies for (bulk tier or loyalty), never both. See ADR-0002.
- Money is rounded half-to-even (banker's rounding) at the very end of a
  quote, never per line. See ADR-0002.
- `docs/adr/` is append-only: a changed decision gets a new ADR.
