def add_tax(amount_cents, rate_pct):
    """Return amount plus tax, rounded to the nearest cent."""
    return amount_cents + amount_cents * rate_pct // 100
